# 光电赛的程序文件
import time
import numpy as np
import pandas as pd
from ctypes import *  # import all
import tkinter as tk
from tkinter import filedialog, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import csv
from matplotlib.pylab import mpl
from scipy.ndimage import gaussian_filter1d
# 前期准备_______________________________
mpl.rcParams['axes.unicode_minus'] = False  # 显示负号
mpl.rcParams['font.sans-serif'] = ['SimHei']  # 显示中文

'''采集/刷新时间修改：2000ms：_capture_loop、_for_cal_average这两处要改'''
'''在_capture_loop里调用capture函数采集光谱，调配调用_capture_loop时间，即可调配采集数据时间！'''

class Spectrometer:
    def __init__(self, lib, index=0):
        # 封装在self里的变量，同一个类都可以use:self.xxx引用
        self.lib = lib
        self.index = index
        self.error_code = 0

        devcount = lib.seabreeze_open_all_spectrometers(self.error_code)  # 命令光谱仪打开，打开则返回1，否则返回0
        if devcount == 1:
            print(f"打开光谱仪")
        else:
            lib.seabreeze_close_all_spectrometers(self.error_code)  # 关闭所有光谱仪
            print(f"没有打开光谱仪")

# 独立可变初始化
    def configure(self, integration_time):
        self.integration_time = integration_time
        self.lib.seabreeze_set_integration_time_microsec(self.index, self.error_code, self.integration_time)
        print(f"积分时间设置为 {self.integration_time} μs")

    def load_wavelengths(self):
        air_wavelengths_c = (c_double * 4096)()  # seabreeze,C function,creat a array to accept
        self.lib.seabreeze_get_wavelengths(self.index, self.error_code, air_wavelengths_c, 4096)
        wavelengths = np.ctypeslib.as_array(air_wavelengths_c).astype(np.float64)  # change c type array into numpy
        # print(f"success load wavelength")
        # print(wavelengths)

        return wavelengths  # 单独想拿波长，也可以直接调用 _load_wavelengths()

    def capture_spectrum(self):
        # 采集光谱
        air_lightspec_c = (c_double * 4096)()
        self.lib.seabreeze_get_formatted_spectrum(self.index, self.error_code, air_lightspec_c, 4096)
        intensity = np.ctypeslib.as_array(air_lightspec_c).astype(np.float64)
        # print(f"success load intensity")

        return intensity

    def bg_capture(self):
        air_lightspec_c_bg = (c_double * 4096)()
        self.lib.seabreeze_get_formatted_spectrum(self.index, self.error_code, air_lightspec_c_bg, 4096)
        bg_intensity = np.ctypeslib.as_array(air_lightspec_c_bg).astype(np.float64)
        print(f"success load bg_intensity")

        return bg_intensity


class SignalProcessor:
    def __init__(self, spec, net_intensity, origin_intensity):
        self.spec = spec
        self.wavelengths = self.spec.load_wavelengths()
        self.intensity_net = net_intensity
        self.intensity_origin = origin_intensity

    def calculate_centroid(self):
        total_intensity = np.sum(self.intensity_net)
        if total_intensity == 0:
            raise ValueError("光谱强度总和为0，无法计算质心。")

        wavelengths_centroid = np.sum(self.intensity_net * self.wavelengths)/total_intensity
        intensity_centroid = np.sum(self.intensity_net * self.intensity_net)/total_intensity

        return wavelengths_centroid, intensity_centroid

    # 平滑函数：未使用self参数的时候会在函数名出现波浪线
    def net_gaussian_smoothing(self, sigma):
        return gaussian_filter1d(self.intensity_net, sigma)    # 只需要对净光谱进行高斯滤波就行，不用原始和空气分别平滑！

    def origin_gaussian_smoothing(self, sigma):
        return gaussian_filter1d(self.intensity_origin, sigma)    # 只需要对净光谱进行高斯滤波就行，不用原始和空气分别平滑！



class Plotter:
    def __init__(self, root):

        self.root = root

        # 创建一个Style对象----------------创标签页！
        self.style = ttk.Style()
        # 设置样式
        self.style.configure('TNotebook.Tab', font=('Times New Roman', 18))  # 调整字体和大小
        # 正确地创建带样式的Notebook（就是集合两个标签页的本子）
        self.notebook = ttk.Notebook(self.root, style='TNotebook')
        self.notebook.pack(pady=10, expand=True)
        # 创建标签页
        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text='光谱图')
        self.notebook.add(self.tab2, text='时序图')

        # ============图1
        self.fig1 = Figure(figsize=(10, 6))  # 创建逻辑画布
        self.ax1 = self.fig1.add_subplot(111)
        self.ax1.set_title('光谱图', fontsize=18)
        self.ax1.set_xlim(380, 1100)
        self.ax1.set_ylim(-100, 70000)
        self.ax1.set_xlabel('波长(nm)', fontsize=15)
        self.ax1.set_ylabel('光强（.a.u）', fontsize=15)  # 设置画布画什么

        self.ax1.tick_params(axis='both', labelsize=14)  # 同时设置 x 和 y 轴数字刻度字体大小为12

        self.line_1, = self.ax1.plot([], [], lw=2, color='#FD0404')
        self.line_2, = self.ax1.plot([], [], lw=2, color='#54E78C')

        self.text_centroid = self.ax1.text(0.8, 0.95, '',
                                          transform=self.ax1.transAxes,
                                          fontsize=14, ha='center')

        self.text_cal_result = self.ax1.text(0.8, 0.90, '',
                                            transform=self.ax1.transAxes,
                                            fontsize=14, ha='center')

        # ============图2
        self.fig2 = Figure(figsize=(10, 6))  # 创建逻辑画布
        self.ax2 = self.fig2.add_subplot(111)
        self.ax2.set_title('时序图', fontsize=18)
        self.ax2.set_xlim(0, 180)
        self.ax2.set_ylim(710, 730)
        self.ax2.set_xlabel('时间', fontsize=15)
        self.ax2.set_ylabel('波长(nm)', fontsize=15)  # 设置画布画什么

        self.ax2.tick_params(axis='both', labelsize=14)  # 同时设置 x 和 y 轴数字刻度字体大小为12

        self.line_3 = self.ax2.scatter([], [], s=22, color='r', label='')


        # =====画布1=====
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.tab1)   # 创建物理画布（画在哪，与tk窗口绑定）
        self.canvas1.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)    # 将canvas的tk组件（布局）放到窗口
        # 创建工具栏并放入窗口(工具栏、按钮这些不是画布！不受canvas.get_tk_widget()影响)
        self.toolbar1 = NavigationToolbar2Tk(self.canvas1, self.tab1)
        self.toolbar1.update()
        self.toolbar1.pack(side=tk.BOTTOM, fill=tk.X)    # 导航工具栏放置（满x轴）

        # =====画布2=====
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.tab2)  # 创建物理画布（画在哪，与tk窗口绑定）
        self.canvas2.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)  # 将canvas的tk组件（布局）放到窗口
        # 创建工具栏并放入窗口(工具栏、按钮这些不是画布！不受canvas.get_tk_widget()影响)
        self.toolbar2 = NavigationToolbar2Tk(self.canvas2, self.tab2)
        self.toolbar2.update()
        self.toolbar2.pack(side=tk.BOTTOM, fill=tk.X)  # 导航工具栏放置（满x轴）

        # 放笔记本
        self.notebook.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)


    def plotting(self, x, y1, text1, text2, y2, times, x_list):
        self.line_1.set_data(x, y1)
        self.line_2.set_data(x, y2)
        self.text_centroid.set_text(f"质心：({text1:.2f}，{text2:.2f})")
        # 散点图要用这个设置数据，而非set_data!set_data是线图(对于scatter不能每次只添加一个点，要整个list进行替换)
        # 最简单兼容的方法就是传递两个list（在list里逐渐append数据）
        self.line_3.set_offsets(np.column_stack((times, x_list)))

        self.canvas1.draw()
        self.canvas2.draw()

    def cal_result_plot(self, result):
        if result == "待测":
            self.text_cal_result.set_text(f"计算结果:{result}")

        else:
            self.text_cal_result.set_text(f"计算结果:{result:.4f}")

        self.canvas1.draw()


class App:
    def __init__(self, root: tk.Tk):
        # 主要数据
        self.bg_spec = None
        self.wavelengths = None
        self.current_net_spec = None
        self.original_spec = None
        self.result = "待测"  # 这是点击“计算”的计算结果
        self.centroid_x = []
        self.centroid_y = []
        self.calculate = []
        self.times = []
        self.start_time = None
        self.first = True


        # == 设置窗口 ==
        self.root = root
        self.root.title("动态采集系统")
        self.root.geometry("350x250")

        '''1.初始化模块'''
        # == 初始化光谱仪和spec类 ==
        self.lib = cdll.LoadLibrary('D:/光谱仪资料/sdk4.1/[4] USB Dome/[3] python demo for windows/SeaBreeze.dll')
        self.spec = Spectrometer(self.lib)
        self.spec.configure(integration_time=50 * 1000)  # 50ms积分时间

        '''2.状态控制'''
        self.is_measuring = False
        self.is_paused = False
        self.is_catching = False  # 如不在_init_中初始化变量会有黄色波浪线
        self.is_calculating = False
        self.is_clearing = False


        '''3.创建提示窗ui组件'''
        self._creat_ui_small()    # “_”私有：仅这个类能用

    def _creat_ui_small(self):
        self.message_label = tk.Label(
            self.root,
            text="是否开始进行采集背景",
            font=("SimSun", 20)
        )
        self.message_label.pack(pady=40)

        self.yes_btn1 = tk.Button(self.root, text="是", command=self.bg_measurement, font=("SimSun", 20), width=5, height=1)
        self.no_btn1 = tk.Button(self.root, text="否", command=self.quit_program, font=("SimSun", 20), width=5, height=1)
        self.yes_btn1.pack(side=tk.LEFT, padx=45, pady=20)
        self.no_btn1.pack(side=tk.RIGHT, padx=45, pady=20)

    def start_measurement(self):
        self.root.destroy()  # 关闭提示窗口

        self.is_measuring = True    # 开始测量仅改变is_measuring状态

        self._big_ui_window()  # 打开新窗口显示动态图

    def _big_ui_window(self):
        self.root = tk.Tk()     # 需要用tk.Tk()创建新的Tkinter窗口
        self.root.title("信号分析结果")
        window_width = 950
        window_height = 750
        self.root.geometry(f"{window_width}x{window_height}")

        '''初始化plotter类==(在init内初始化可能会弹出两个窗口或者矛盾？)'''
        self.plotter = Plotter(self.root)


        # 在窗口工具栏处创建暂停、导出数据按钮
        self.paused_btn = tk.Button(self.plotter.toolbar1, text="暂停/继续", command=self.toggle_pause)
        self.paused_btn.pack(side=tk.LEFT, padx=4, pady=2)
        self.export_btn = tk.Button(self.plotter.toolbar1, text="数据导出", command=self.export_data)
        self.export_btn.pack(side=tk.LEFT, padx=4, pady=2)
        self.catch_btn = tk.Button(self.plotter.toolbar1, text="采集", command=self.catch_data)
        self.catch_btn.pack(side=tk.LEFT, padx=4, pady=2)
        self.calculate_btn = tk.Button(self.plotter.toolbar1, text="计算", command=self.cal_average)
        self.calculate_btn.pack(side=tk.LEFT, padx=4, pady=2)
        self.clear_btn = tk.Button(self.plotter.toolbar1, text="清除", command=self.clear)
        self.clear_btn.pack(side=tk.LEFT, padx=4, pady=2)


        # 循环采集、信号处理、显示
        self._capture_loop()

    def bg_measurement(self):
        self.bg_spec = self.spec.bg_capture()
        self.wavelengths = self.spec.load_wavelengths()

        self.message_label.config(text="采集完成，是否开始测量？", font=("SimSun", 18))  # .config()更新文字提示
        self.yes_btn1.config(command=self.start_measurement)  # 更换按钮指令
        self.no_btn1.config(command=self.quit_program)

    def quit_program(self):
        self.root.quit()
        self.lib.seabreeze_close_all_spectrometers(error_code)  # 关闭所有光谱仪

    def _capture_loop(self):
        if not self.is_measuring or self.is_paused:
            return

        '''初始化信号处理类'''
        self.original_spec = self.spec.capture_spectrum()
        self.current_net_spec = self.original_spec - self.bg_spec  # 净光谱传输
        self.signal_process = SignalProcessor(self.spec, self.current_net_spec, self.original_spec)

        temp_centroid_x, temp_centroid_y = self.signal_process.calculate_centroid()
        self.centroid_x.append(temp_centroid_x)
        self.centroid_y.append(temp_centroid_y)

        intensity_gauss_filtered1 = self.signal_process.net_gaussian_smoothing(22)      # 调节sigma参数
        intensity_gauss_filtered2 = self.signal_process.origin_gaussian_smoothing(22)

        # 只执行一次操作（记录初始时间，后面的时间作差）
        if self.first:
            self.start_time = time.time()
            self.first = False

        current_time = time.time()-self.start_time
        self.times.append(current_time)

        # 显示
        self.plotter.plotting(self.wavelengths,
                              intensity_gauss_filtered1,
                              temp_centroid_x,
                              temp_centroid_y,
                              intensity_gauss_filtered2,
                              self.times,
                              self.centroid_x)

        if not self.is_calculating:
            self.plotter.cal_result_plot(self.result)

        self.root.after(2000, self._capture_loop)    # 每隔100ms调用一次_capture_loop

    def _for_catch_btn(self):
        if not self.is_catching:
            return

        self.calculate.append(self.centroid_x[-2])
        self.calculate.append(self.centroid_x[-1])  # 最新两个元素
        self.is_catching = False
        print(self.centroid_x[-2], self.centroid_x[-1])

    def _for_cal_average(self):
        if not self.is_calculating:
            return

        if len(self.calculate) == 0:
            print("你没有点击采集数据！")
            self.is_calculating = not self.is_calculating
            print(self.is_calculating)

        else:
            if any(isinstance(x, list) for x in self.calculate):
                self.calculate = [item for sublist in self.calculate for item in sublist]

            self.result = sum(self.calculate) / len(self.calculate)
            self.plotter.cal_result_plot(self.result)

            self.is_calculating = not self.is_calculating
            self.root.after(2000, self._for_cal_average)

    def _for_clear_data(self):
        if not self.is_clearing:
            return

        self.calculate = []
        self.result = "待测"
        # self.is_calculating = not self.is_calculating
        self.is_clearing = not self.is_clearing

        self.plotter.cal_result_plot(self.result)

        print("calculate已经清空！")

    def toggle_pause(self):
        self.is_paused = not self.is_paused     # 继续就是多按一下

        if not self.is_paused:
            self._capture_loop()

    # def export_data(self):
    #     if self.current_net_spec is None:
    #         print(f"NO DATA!")
    #         return
    #
    #     # 统一取最短的长度，避免索引越界
    #     min_len = min(len(self.centroid_x), len(self.centroid_y))
    #
    #     filepath = filedialog.asksaveasfilename(
    #         defaultextension=".csv",
    #         filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
    #     )
    #     if filepath:
    #         with open(filepath, 'w', newline='') as f:
    #             writer = csv.writer(f)
    #             writer.writerow(["质心X坐标", "质心Y坐标"])
    #             for i in range(min_len):
    #                 writer.writerow([self.centroid_x[i], self.centroid_y[i]])
    #         print("成功导出数据！")

    def export_data(self):
        if self.current_net_spec is None:
            print("NO DATA!")
            return

        min_len = min(len(self.centroid_x), len(self.centroid_y))

        # 构建 DataFrame
        df = pd.DataFrame({
            "质心X坐标": self.centroid_x[:min_len],
            "质心Y坐标": self.centroid_y[:min_len]
        })

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        if filepath:
            try:
                df.to_excel(filepath, index=False)
                print("成功导出数据为 Excel 文件！")
            except Exception as e:
                print("导出失败:", e)

    def catch_data(self):
        self.is_catching = not self.is_catching

        if self.is_catching:
            self._for_catch_btn()

    def cal_average(self):
        self.is_calculating = not self.is_calculating

        if self.is_calculating:
            self._for_cal_average()

    def clear(self):
        self.is_clearing = not self.is_clearing

        if self.is_clearing:
            self._for_clear_data()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    app.run()



