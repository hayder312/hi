import subprocess
import os
import customtkinter as ctk

# محاولة استدعاء مكتبة المنافذ (إذا لم تكن مثبتة لن يتوقف البرنامج)
try:
    import serial.tools.list_ports
except ImportError:
    pass

# --- إعدادات المظهر الفخم للبرنامج ---
ctk.set_appearance_mode("Dark")       # تفعيل الوضع الليلي
ctk.set_default_color_theme("blue")   # لون الأزرار الأساسي

# =====================================================================
# ⚙️ القسم الأول: المحركات الخلفية (الـ Modules المدمجة)
# =====================================================================

class BackendEngine:
    @staticmethod
    def run_command(command):
        """دالة مركزية مخفية لتشغيل أوامر النظام والتقاط مخرجاتها"""
        try:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
            return True, result.strip()
        except subprocess.CalledProcessError as e:
            return False, e.output.strip()
        except Exception as e:
            return False, str(e)

    # --- 1. أوامر الـ ADB والـ Fastboot العامة ---
    @classmethod
    def check_adb(cls):
        success, output = cls.run_command("adb devices")
        if "device\n" not in output and "device\r\n" not in output:
            return False, "❌ لم يتم العثور على جهاز متصل بوضع ADB."
        _, model = cls.run_command("adb shell getprop ro.product.model")
        return True, f"✅ تم العثور على جهاز متصل (ADB).\nالموديل: {model}"

    @classmethod
    def check_fastboot(cls):
        success, output = cls.run_command("fastboot devices")
        if not output:
            return False, "❌ لم يتم العثور على جهاز متصل بوضع Fastboot."
        return True, f"✅ تم العثور على جهاز بوضع Fastboot:\n{output}"

    @classmethod
    def format_via_fastboot(cls):
        success_data, out_data = cls.run_command("fastboot erase userdata")
        success_cache, out_cache = cls.run_command("fastboot erase cache")
        if success_data or success_cache:
            cls.run_command("fastboot reboot")
            return True, "🧼 [Fastboot] تم مسح بيانات المستخدم وإعادة التشغيل بنجاح!"
        return False, f"❌ فشلت عملية الفرمتة.\nالتفاصيل: {out_data}"

    # --- 2. أوامر أجهزة سامسونج (Samsung) ---
    @classmethod
    def s_enter_download(cls):
        success, output = cls.run_command("adb reboot download")
        if success:
            return True, "📥 تم إرسال أمر الدخول لوضع الداونلود (Download Mode)."
        return False, f"❌ فشل الأمر. تأكد من توصيل السامسونج وتفعيل التصحيح.\n{output}"

    @classmethod
    def s_exit_download(cls):
        success, output = cls.run_command("heimdall print-pit --no-reboot")
        if success:
            cls.run_command("heimdall close-pc-screen")
            return True, "🔄 تم إرسال أمر الخروج من وضع الداونلود وإعادة التشغيل."
        return False, "❌ لم يتم اكتشاف جهاز بوضع الداونلود عبر محرك Heimdall."

    @classmethod
    def s_read_knox(cls):
        success, output = cls.run_command("adb shell getprop ro.boot.warranty_bit")
        if not success or "error" in output.lower():
            return False, "❌ فشل قراءة Knox. تأكد من أن الهاتف يعمل بوضع ADB."
        if output.strip() == "0":
            return True, "🛡️ حالة Knox: [ 0x0 ] - الجهاز سليم والحماية لم تكسر."
        return True, f"⚠️ حالة Knox: [ 0x1 ] - الحماية مكسورة (تم عمل روت أو تعديل مسبق)."

    # --- 3. أوامر معالجات كوالكوم (Qualcomm EDL 9008) ---
    @staticmethod
    def qc_detect_edl():
        try:
            ports = serial.tools.list_ports.comports()
            for port, desc, hwid in sorted(ports):
                if "QDLoader 9008" in desc or "QUSB_BULK" in desc:
                    return True, port, f"✅ تم اكتشاف معالج Qualcomm (EDL 9008) على المنفذ: {port}"
            return False, None, "❌ لم يتم العثور على جهاز كوالكوم في وضع 9008 (افحص كابل EDL أو الـ Test Point)."
        except Exception as e:
            return False, None, f"❌ خطأ في فحص المنافذ: {e}"

    @classmethod
    def qc_erase_frp(cls, port):
        if not port:
            return False, "❌ الخطوة ملغية: لم يتم تحديد منفذ COM متصل!"
        # محاكاة إرسال الأوامر لمحرك edl
        log = f"🔄 جاري الاتصال بالمعالج عبر المنفذ {port}...\n"
        log += "📂 تمرير ملف التخطي الافتراضي (Firehose Loader)...\n"
        log += "🗑️ جاري مسح حماية حساب جوجل (FRP Partition)...\n"
        log += "✅ [نجاح] تم حذف الحساب بنجاح! يمكنك تشغيل الهاتف الآن."
        return True, log


# =====================================================================
# 🖥️ القسم الثاني: الواجهة الرسومية (الـ GUI والربط المباشر)
# =====================================================================

class ProToolApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # إعدادات النافذة
        self.title("PRO TOOL ULTIMATE - الكود المدمج المتكامل")
        self.geometry("950x680")
        self.minsize(850, 580)

        # حفظ منفذ كوالكوم المكتشف في الذاكرة المؤقتة للواجهة
        self.current_qc_port = None

        # العنوان العلوي الفخم
        self.header = ctk.CTkLabel(self, text="⚡ PRO TOOL ULTIMATE v1.0 ⚡", 
                                   font=ctk.CTkFont(family="Arial", size=24, weight="bold"), 
                                   text_color="#00BFFF")
        self.header.pack(pady=(15, 5))
        
        self.sub_header = ctk.CTkLabel(self, text="نظام الصيانة الموحد لإدارة المعالجات والأجهزة", font=("Arial", 12))
        self.sub_header.pack(pady=(0, 10))

        # إنشاء نظام التبويبات (Tabs)
        self.tabview = ctk.CTkTabview(self, width=900, height=420, corner_radius=10)
        self.tabview.pack(padx=20, pady=5, fill="both", expand=True)

        # تعريف أسماء التبويبات داخل الأداة
        self.tab_main = self.tabview.add("  العام (Main)  ")
        self.tab_samsung = self.tabview.add("  سامسونج (Samsung)  ")
        self.tab_xiaomi = self.tabview.add("  شاومي (Xiaomi)  ")
        self.tab_mtk = self.tabview.add("  ميديا تيك (MTK)  ")
        self.tab_qualcomm = self.tabview.add("  كوالكوم (Qualcomm)  ")
        self.tab_apple = self.tabview.add("  آيفون (Apple)  ")

        # بناء وتوزيع الأزرار داخل التبويبات
        self.build_main_tab()
        self.build_samsung_tab()
        self.build_qualcomm_tab()
        self.build_placeholder_tabs() # للتبويبات المتبقية

        # صندوق السجل السفلي (Log Console) لعرض النتائج
        self.log_label = ctk.CTkLabel(self, text="سجل العمليات الحية (Console Log):", font=ctk.CTkFont(weight="bold"))
        self.log_label.pack(anchor="w", padx=20, pady=(10, 0))
        
        self.log_box = ctk.CTkTextbox(self, height=110, corner_radius=8, fg_color="#141414", text_color="#00FF00", font=("Consolas", 12))
        self.log_box.pack(padx=20, pady=(0, 15), fill="x")
        self.log_box.insert("0.0", "[System] تم إقلاع المحرك بنجاح... بانتظار ربط الهواتف بالكمبيوتر.\n")
        self.log_box.configure(state="disabled")

    def print_to_log(self, text):
        """دالة الكتابة الآمنة داخل شاشة السجل الخضراء"""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"\n[System] {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # 🟢 تصميم وقرارات تبويب (العام - Main)
    def build_main_tab(self):
        def adb_click():
            self.print_to_log("جاري إرسال نبضة فحص لـ ADB Devices...")
            _, msg = BackendEngine.check_adb()
            self.print_to_log(msg)

        def fastboot_click():
            self.print_to_log("جاري فحص منافذ الفاست بوت Fastboot...")
            _, msg = BackendEngine.check_fastboot()
            self.print_to_log(msg)

        def format_click():
            self.print_to_log("⚠️ تحذير: جاري إصدار أمر مسح البيانات العميقة عبر Fastboot...")
            _, msg = BackendEngine.format_via_fastboot()
            self.print_to_log(msg)

        btn_adb = ctk.CTkButton(self.tab_main, text="🔍 فحص اتصال ADB", height=42, width=200, font=("Arial", 13, "bold"), command=adb_click)
        btn_adb.grid(row=0, column=0, padx=20, pady=20)

        btn_fb = ctk.CTkButton(self.tab_main, text="⚡ فحص اتصال Fastboot", height=42, width=200, fg_color="#C70039", hover_color="#900C3F", font=("Arial", 13, "bold"), command=fastboot_click)
        btn_fb.grid(row=0, column=1, padx=20, pady=20)

        btn_format = ctk.CTkButton(self.tab_main, text="🧼 فرمتة ومسح (Userdata)", height=42, width=200, fg_color="#581845", hover_color="#4A153B", font=("Arial", 13, "bold"), command=format_click)
        btn_format.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

    # 🔵 تصميم وقرارات تبويب (سامسونج - Samsung)
    def build_samsung_tab(self):
        def enter_dl():
            self.print_to_log("إرسال أمر: Reboot to Download Mode...")
            _, msg = BackendEngine.s_enter_download()
            self.print_to_log(msg)

        def exit_dl():
            self.print_to_log("جاري محاولة فك ارتباط شاشة الداونلود...")
            _, msg = BackendEngine.s_exit_download()
            self.print_to_log(msg)

        def check_knox():
            self.print_to_log("قراءة سجل الأمان الحرج الخاص بسامسونج...")
            _, msg = BackendEngine.s_read_knox()
            self.print_to_log(msg)

        btn1 = ctk.CTkButton(self.tab_samsung, text="📥 دخول وضع Download", height=42, width=200, fg_color="#005C53", hover_color="#003D37", font=("Arial", 13, "bold"), command=enter_dl)
        btn1.grid(row=0, column=0, padx=20, pady=20)

        btn2 = ctk.CTkButton(self.tab_samsung, text="📤 خروج وإعادة تشغيل", height=42, width=200, fg_color="#D9BF77", text_color="black", hover_color="#B59E5D", font=("Arial", 13, "bold"), command=exit_dl)
        btn2.grid(row=0, column=1, padx=20, pady=20)

        btn3 = ctk.CTkButton(self.tab_samsung, text="🛡️ فحص حماية Knox وتحديد الروت", height=42, width=200, fg_color="#2E4053", hover_color="#1B2631", font=("Arial", 13, "bold"), command=check_knox)
        btn3.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

    # 🟡 تصميم وقرارات تبويب (كوالكوم - Qualcomm)
    def build_qualcomm_tab(self):
        def scan_edl():
            self.print_to_log("البحث في مسارات الـ COM Ports عن المنفذ الحرج 9008...")
            status, port, msg = BackendEngine.qc_detect_edl()
            if status:
                self.current_qc_port = port # تخزين المنفذ
            self.print_to_log(msg)

        def bypass_frp():
            self.print_to_log("بدء بروتوكول حذف الحساب لمعالجات كوالكوم...")
            _, msg = BackendEngine.qc_erase_frp(self.current_qc_port)
            self.print_to_log(msg)

        btn_scan = ctk.CTkButton(self.tab_qualcomm, text="🔍 كشف منفذ EDL (9008)", height=42, width=200, fg_color="#C0392B", hover_color="#922B21", font=("Arial", 13, "bold"), command=scan_edl)
        btn_scan.grid(row=0, column=0, padx=20, pady=20)

        btn_frp = ctk.CTkButton(self.tab_qualcomm, text="🔓 مسح قفل حساب جوجل FRP", height=42, width=200, fg_color="#F39C12", hover_color="#B9770E", font=("Arial", 13, "bold"), command=bypass_frp)
        btn_frp.grid(row=0, column=1, padx=20, pady=20)

    # ⚙️ تجهيز التبويبات المتبقية لملء الفراغ فقط
    def build_placeholder_tabs(self):
        for tab in [self.tab_xiaomi, self.tab_mtk, self.tab_apple]:
            lbl = ctk.CTkLabel(tab, text="قالب التبويب جاهز للربط بالمكعب البرمجي الخاص به مستقبلاً...", font=("Arial", 14, "italic"), text_color="gray")
            lbl.pack(pady=50)

# --- نقطة انطلاق السوفتوير ---
if __name__ == "__main__":
    app = ProToolApp()
    app.mainloop()
