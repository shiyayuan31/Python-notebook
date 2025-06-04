## 光学项目代码

>💡：此处仅展示<u>部分代码</u>，完整代码本人已托管至Github仓库作为开源代码，供其他开发者使用同时得到反馈，以便不断完善方案、提高笔者个人能力。

Github仓库链接：<https://github.com/shiyayuan31/Python-notebook>


#### 项目1：共聚焦显微镜测量微小位移
运用OOP风格，代码实现了一个**基于光谱仪的信号采集与分析系统**，主要功能包括：
1.**硬件控制**：通过SeaBreeze库控制光谱仪设备，设置积分时间并获取光谱数据
2.**信号处理**：计算光谱质心、高斯平滑滤波等处理
3.**可视化界面**：使用Tkinter构建GUI，Matplotlib实时显示光谱曲线和质心位置
4.**数据管理**：支持暂停/继续采集、数据导出、多组数据平均计算等功能
>系统工作流程：初始化设备→采集背景光谱→实时测量显示→数据处理分析。适用于需要光谱采集和实时分析的实验场景。

##### 部分代码
```Python
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
    def gaussian_smoothing(self, sigma):
        return gaussian_filter1d(self.intensity_net, sigma)    # 只需要对净光谱进行高斯滤波就行，不用原始和空气分别平滑！

'''省略'''

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    app.run()
```

##### 效果图

#### 项目2：光纤传感器双信号调制、动态追踪


```Python
 def process_and_update():
        wavelengths_M = []
        wavelengths_S = []
        times = []
        wavelengths_shifts = []
        start_time = time.time()
        while devcount > 0:
            # 取数据————————————————————————
            index = 0
            lib.seabreeze_set_integration_time_microsec(index, error_code, integration_time)  # 设置积分时间

            wavelengths_c = (c_double * 4096)()
            lib.seabreeze_get_wavelengths(index, error_code, wavelengths_c, 4096)  # 获取波长
            wavelengths_np = np.ctypeslib.as_array(wavelengths_c).astype(np.float64)  # 波长转换类型（c-numpy类型）

            lightspec_c = (c_double * 4096)()
            lib.seabreeze_get_formatted_spectrum(index, error_code, lightspec_c, 4096)  # 获取亮光谱（未去除背景）
            lightspec_np = np.ctypeslib.as_array(lightspec_c).astype(np.float64)  # 波长转换类型（c-numpy类型）
            # 数据处理—————————————————————
            # 记录原始图
            # 【线性插值】（使不均匀变均匀）
            interpolated_intensity_M = np.interp(interp_wavelengths, wavelengths_np, lightspec_np)

            intensity_S = savitzky_golay_smoothing(lightspec_np, 11, 3)
            interpolated_intensity_S = np.interp(interp_wavelengths, wavelengths_np, intensity_S)

            # 显示的原始谱：高平滑
            show_intensity = savitzky_golay_smoothing(interpolated_intensity_M, 20, 7)

            # SPR
            spr_intensity = interpolated_intensity_S / air_interpolated_intensity  # spr除去空气谱原始光强(空气减溶液，正值)

            # 【傅里叶变换】
            # MMI
            fft_result_M = fft(interpolated_intensity_M)  # fft_result是复数，alt取模
            # 此处用于fft图显示，暂不需要
            # alt1 = np.abs(fft_result_M) / n  # 归一化(两种fft常见归一化：1，除以点数；2，除以点数的平方根；此处用1)
            # SPR
            fft_result_S = fft(spr_intensity)
            temp_alt = np.abs(fft_result_S) / n
            # 此处用于fft图显示，暂不需要
            # alt2 = (temp_alt - min(temp_alt)) / (max(temp_alt) - min(temp_alt))
            # 【简单滤波】（手动设置，固定；但是范围精确度影响ifft结果细节“边缘效应”）：保留兴趣峰其他置0
            # MMI__________________________________________________________
            idx_low = np.argmin(np.abs(freqs - lowcut))
            idx_high = np.argmin(np.abs(freqs - highcut))

            if idx_low < 0:
                idx_low = 0
            if idx_high >= len(freqs):
                idx_high = len(freqs) - 1
            if idx_high < idx_low:
                idx_high, idx_low = idx_low, idx_high

            fft_filtered_M = np.zeros_like(fft_result_M, dtype=np.complex128)
            fft_filtered_M[idx_low:idx_high + 1] = fft_result_M[idx_low:idx_high + 1]
            fft_filtered_M[-idx_high:-idx_low + 1] = fft_result_M[-idx_high:-idx_low + 1]

            # 去除直流成分
            fft_filtered_M[0] = 0

            # 【逆傅里叶变换】
            ifft_result_M = np.real(ifft(fft_filtered_M))  # 取实部

            max_index_M = np.argmax(ifft_result_M)  # 找到ifft_result最大值的索引
            wavelength_M = interp_wavelengths[max_index_M]
            wavelengths_M.append(wavelength_M)
            delta_M = wavelengths_M[-1] - wavelengths_M[0]

            # SPR___________________________________________________________
            idx_spr = np.argmin(np.abs(freqs - spr_cut))  # 定位spr_cut频率值对应索引值

            # 用于运算数组（实际输出）
            fft_filtered_S = np.zeros_like(fft_result_S, dtype=np.complex128)
            fft_filtered_S[1:idx_spr + 1] = fft_result_S[1:idx_spr + 1]

            # 【逆傅里叶变换】
            temp_result = np.real(ifft(fft_filtered_S))
            ifft_result_S = (temp_result - min(temp_result)) / (max(temp_result) - min(temp_result))  # 取实部

    '''省略'''
```
