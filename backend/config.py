"""
إعدادات وبيانات ثابتة للأداة: قائمة الأسهم النشطة الظاهرة في مرجع أسهم EGX المتداولة
(مراجعة 2026-10-05)، مقسّمة حسب القطاع، وخريطة الأكواد البديلة (ISIN)
لياهو فاينانس، وإعدادات الأطر الزمنية المتاحة للفحص.
"""

EGX_MARKET_BY_SECTOR = {
    "البنوك": [
        {"ticker": "COMI.CA", "name": "البنك التجاري الدولي (CIB)"},
        {"ticker": "ADIB.CA", "name": "مصرف أبو ظبي الإسلامي - مصر"},
        {"ticker": "QNBA.CA", "name": "بنك قطر الوطني (QNB)"},
        {"ticker": "CIEB.CA", "name": "بنك كريدي أجريكول مصر"},
        {"ticker": "EXPA.CA", "name": "البنك المصري لتنمية الصادرات (EBank)"},
        {"ticker": "HDBK.CA", "name": "بنك التعمير والإسكان"},
        {"ticker": "CANA.CA", "name": "بنك قناة السويس"},
        {"ticker": "SAUD.CA", "name": "بنك البركة مصر"},
        {"ticker": "SAIB.CA", "name": "بنك الشركة المصرفية العربية (SAIB)"},
        {"ticker": "EGBE.CA", "name": "البنك المصري الخليجي (إيجي بنك)"},
        {"ticker": "FAITA.CA", "name": "بنك فيصل الإسلامي المصري (الفئة الأخرى)"},
        {"ticker": "QNBE.CA", "name": "بنك قطر الوطني الأهلي (QNBE)"},
        {"ticker": "FAIT.CA", "name": "بنك فيصل الإسلامي المصري (الفئة الرئيسية)"},
        {"ticker": "UBEE.CA", "name": "البنك المتحد"},
        {"ticker": "NBKE.CA", "name": "بنك الكويت الوطني - مصر"},
        {"ticker": "UNBE.CA", "name": "البنك الأهلي المتحد - مصر"},
    ],
    "الخدمات المالية غير المصرفية والصناديق": [
        {"ticker": "FWRY.CA", "name": "فوري لتكنولوجيا البنوك والمدفوعات الإلكترونية"},
        {"ticker": "HRHO.CA", "name": "إي إف جي القابضة (هيرمس)"},
        {"ticker": "EFIH.CA", "name": "إي فاينانس للاستثمارات المالية والرقمية"},
        {"ticker": "EKHO.CA", "name": "القابضة المصرية الكويتية (بالجنيه)"},
        {"ticker": "EKHOA.CA", "name": "القابضة المصرية الكويتية (بالدولار)"},
        {"ticker": "CICH.CA", "name": "سي آي كابيتال القابضة"},
        {"ticker": "BTFH.CA", "name": "بلتون القابضة"},
        {"ticker": "CCAP.CA", "name": "القلعة للاستثمارات المالية"},
        {"ticker": "ACTF.CA", "name": "أكت فايننشال"},
        {"ticker": "BINV.CA", "name": "بي إنفستمنتس القابضة"},
        {"ticker": "VLMRA.CA", "name": "فالمور القابضة للاستثمار (VLMRA)"},
        {"ticker": "ATLC.CA", "name": "التوفيق للتأجير التمويلي"},
        {"ticker": "OIH.CA", "name": "أوراسكوم للاستثمار القابضة"},
        {"ticker": "PRMH.CA", "name": "برايم القابضة للاستثمارات المالية"},
        {"ticker": "VALU.CA", "name": "فاليو لتمويل المستهلك"},
        {"ticker": "CNFN.CA", "name": "كونتاكت المالية القابضة"},
        {"ticker": "ACAP.CA", "name": "إيه كابيتال القابضة"},
        {"ticker": "OFH.CA", "name": "أو بي القابضة المالية"},
        {"ticker": "NAHO.CA", "name": "نعيم القابضة للاستثمارات (منطقة حرة)"},
        {"ticker": "ACAMD.CA", "name": "العربية لإدارة وتنمية الأصول"},
        {"ticker": "AMIA.CA", "name": "الملتقى العربي للاستثمارات (أميا)"},
        {"ticker": "MAAL.CA", "name": "مرسيليا المصرية الخليجية القابضة للاستثمار"},
        {"ticker": "ICID.CA", "name": "الدولية للاستثمار والتنمية"},
        {"ticker": "SEIG.CA", "name": "السعودية المصرية للاستثمار والتمويل (بالجنيه)"},
        {"ticker": "SEIGA.CA", "name": "السعودية المصرية للاستثمار والتمويل (بالدولار)"},
        {"ticker": "TYCN.CA", "name": "تايكون القابضة للاستثمارات المالية"},
        {"ticker": "ICLE.CA", "name": "الدولية للتأجير التمويلي"},
        {"ticker": "AIHC.CA", "name": "أرابيا القابضة للاستثمارات"},
        {"ticker": "EASB.CA", "name": "العربية المصرية (ثمار) للوساطة في الأوراق المالية"},
        {"ticker": "GRCA.CA", "name": "جراند كابيتال للاستثمارات المالية"},
        {"ticker": "EBSC.CA", "name": "أصول ESB للوساطة في الأوراق المالية"},
        {"ticker": "EOSB.CA", "name": "العروبة للوساطة في الأوراق المالية"},
        {"ticker": "CPME.CA", "name": "كاتاليست بارتنرز"},
        {"ticker": "ASPI.CA", "name": "أسباير كابيتال القابضة للاستثمارات المالية"},
        {"ticker": "GTEX.CA", "name": "جي تكس للاستثمارات التجارية والصناعية"},
        {"ticker": "GMCI.CA", "name": "جي إم سي جروب للاستثمارات الصناعية والتجارية والمالية"},
        {"ticker": "AIDC.CA", "name": "أرابيا للاستثمار والتنمية"},
        {"ticker": "GBCO.CA", "name": "جي بي كورب (جي بي أوتو سابقاً)"},
        {"ticker": "ODIN.CA", "name": "أودين للاستثمارات"},
        {"ticker": "KWIN.CA", "name": "القاهرة الوطنية للاستثمار"},
        {"ticker": "ABRD.CA", "name": "المصريين بالخارج للاستثمار والتنمية"},
        {"ticker": "AGIN.CA", "name": "الخليج العربي للاستثمار"},
        {"ticker": "AIND.CA", "name": "أرابيا للاستثمارات التنموية القابضة"},
        {"ticker": "AITG.CA", "name": "أسيوط الإسلامية الوطنية للتجارة والتنمية"},
        {"ticker": "AIVCB.CA", "name": "العربي للاستثمار والاستشارات (بالجنيه)"},
        {"ticker": "ANFI.CA", "name": "الإسكندرية الوطنية للاستثمارات المالية"},
        {"ticker": "BCAP.CA", "name": "بلتون كابيتال القابضة للاستثمارات المالية"},
        {"ticker": "CCAPP.CA", "name": "القلعة للاستثمارات المالية (أسهم ممتازة)"},
        {"ticker": "CIRF.CA", "name": "القاهرة للتنمية والاستثمار"},
        {"ticker": "IBCT.CA", "name": "الدولية للأعمال التجارية والامتياز"},
        {"ticker": "LKGP.CA", "name": "مجموعة لكح"},
        {"ticker": "MEDA.CA", "name": "مصر السلام للتنمية والتكنولوجيا المتقدمة"},
        {"ticker": "MFINEG.CA", "name": "مصر للاستثمارات المالية"},
        {"ticker": "NCIN.CA", "name": "النيل سيتي للاستثمار"},
        {"ticker": "ODID.CA", "name": "أودين للاستثمار والتنمية"},
        {"ticker": "REAC.CA", "name": "ريكاب للاستثمارات المالية"},
        {"ticker": "SRWA.CA", "name": "ساروا كابيتال (التمويل متناهي الصغر)"}
    ],
    "التأمين": [
        {"ticker": "MOIN.CA", "name": "المهندس للتأمين"},
        {"ticker": "DEIN.CA", "name": "دلتا للتأمين"}
    ],
    "العقارات والإنشاءات": [
        {"ticker": "TMGH.CA", "name": "مجموعة طلعت مصطفى القابضة"},
        {"ticker": "PHDC.CA", "name": "بالم هيلز للتعمير"},
        {"ticker": "OCDI.CA", "name": "السادس من أكتوبر للتنمية (سوديك)"},
        {"ticker": "MNHD.CA", "name": "مدينة مصر (مدينة نصر للإسكان سابقاً)"},
        {"ticker": "HELI.CA", "name": "مصر الجديدة للإسكان والتعمير"},
        {"ticker": "EMFD.CA", "name": "إعمار مصر للتنمية"},
        {"ticker": "ORHD.CA", "name": "أوراسكوم للتنمية مصر"},
        {"ticker": "PRDC.CA", "name": "بايونيرز بروبرتيز للتنمية العمرانية"},
        {"ticker": "UNIT.CA", "name": "المتحدة للإسكان والتعمير"},
        {"ticker": "ELSH.CA", "name": "الشمس للإسكان والتعمير"},
        {"ticker": "ORAS.CA", "name": "أوراسكوم كونستراكشون"},
        {"ticker": "NCCW.CA", "name": "النصر للأعمال المدنية"},
        {"ticker": "ARAB.CA", "name": "المطورون العرب القابضة"},
        {"ticker": "ZMID.CA", "name": "زهراء المعادي للاستثمار والتعمير"},
        {"ticker": "EGTS.CA", "name": "المصرية للمنتجعات السياحية"},
        {"ticker": "GGCC.CA", "name": "الجيزة العامة للمقاولات"},
        {"ticker": "RREI.CA", "name": "رواد السياحة (الرواد)"},
        {"ticker": "EHDR.CA", "name": "المصريين للإسكان والتنمية"},
        {"ticker": "GPPL.CA", "name": "جولدن بيراميدز بلازا (مول سيتي ستارز)"},
        {"ticker": "MASR.CA", "name": "مدينة مصر للإسكان والتعمير"},
        {"ticker": "BONY.CA", "name": "بنيان للتنمية والتجارة"},
        {"ticker": "CRST.CA", "name": "كريست مارك للمقاولات والاستثمار العقاري"},
        {"ticker": "ELKA.CA", "name": "القاهرة للإسكان والتعمير"},
        {"ticker": "NARE.CA", "name": "نعيم العقارية القابضة"},
        {"ticker": "GPIM.CA", "name": "جي بي آي للتنمية العمرانية"},
        {"ticker": "IDRE.CA", "name": "الإسماعيلية للتنمية والاستثمار العقاري"},
        {"ticker": "UEGC.CA", "name": "السعيد للمقاولات والاستثمار العقاري"},
        {"ticker": "NHPS.CA", "name": "الوطنية لإسكان النقابات المهنية"},
        {"ticker": "OBRI.CA", "name": "الأبعادية (الإيبور) للاستثمار العقاري"},
        {"ticker": "AFDI.CA", "name": "الأهلي للتنمية والاستثمار"},
        {"ticker": "TANM.CA", "name": "التنمية للاستثمار العقاري"},
        {"ticker": "AREH.CA", "name": "المجمع العربي للاستثمار العقاري"},
        {"ticker": "CCRS.CA", "name": "الخليج الكندية للاستثمار العقاري العربي"},
        {"ticker": "GIHD.CA", "name": "الغربية الإسلامية للتنمية العقارية"},
        {"ticker": "ELWA.CA", "name": "الوادي للتنمية الدولية والاستثمار"},
        {"ticker": "ENGC.CA", "name": "الهندسية الصناعية للمقاولات والتنمية (ICON)"},
        {"ticker": "DAPH.CA", "name": "التنمية والاستشارات الهندسية"},
        {"ticker": "COPR.CA", "name": "كوبر للاستثمار التجاري والتنمية العقارية"},
        {"ticker": "AREHA.CA", "name": "المجمع العربي للاستثمار العقاري (أسهم لحاملها)"},
        {"ticker": "BSFR.CA", "name": "إخوة التضامن للاستثمار العقاري والأمن الغذائي"},
        {"ticker": "DCRC.CA", "name": "الدلتا للإنشاءات وإعادة البناء"},
        {"ticker": "EIUD.CA", "name": "المصريين للاستثمار والتنمية العمرانية"},
        {"ticker": "FIRED.CA", "name": "الاستثمار العقاري الأول والتنمية"},
        {"ticker": "FNAR.CA", "name": "الفنار للمقاولات والإنشاءات والتجارة"},
        {"ticker": "NOAF.CA", "name": "شمال أفريقيا للاستثمار العقاري"},
        {"ticker": "OCIC.CA", "name": "أوراسكوم للإنشاءات الصناعية"},
        {"ticker": "UTOP.CA", "name": "يوتوبيا للاستثمار العقاري والسياحي"},
    ],
    "المواد الأساسية": [
        {"ticker": "MFPC.CA", "name": "موبكو (مصر لإنتاج الأسمدة)"},
        {"ticker": "ABUK.CA", "name": "أبو قير للأسمدة والصناعات الكيماوية"},
        {"ticker": "SKPC.CA", "name": "سيدي كرير للبتروكيماويات (سيدبك)"},
        {"ticker": "ESRS.CA", "name": "حديد عز"},
        {"ticker": "EGAL.CA", "name": "مصر للألومنيوم"},
        {"ticker": "KIMA.CA", "name": "كيما (الصناعات الكيماوية المصرية)"},
        {"ticker": "ATQA.CA", "name": "مصر الوطنية للصلب (عتاقة)"},
        {"ticker": "ASCM.CA", "name": "أسمنت سينا"},
        {"ticker": "ARCC.CA", "name": "العربية للأسمنت"},
        {"ticker": "SVCE.CA", "name": "جنوب الوادي للأسمنت"},
        {"ticker": "SCEM.CA", "name": "أسمنت سيناء"},
        {"ticker": "MCQE.CA", "name": "مصر للأسمنت - قنا"},
        {"ticker": "EFIC.CA", "name": "المالية والصناعية المصرية"},
        {"ticker": "IRON.CA", "name": "الحديد والصلب المصرية"},
        {"ticker": "ISMQ.CA", "name": "الحديد والصلب للمناجم والمحاجر"},
        {"ticker": "FERC.CA", "name": "فيرشيم مصر للأسمدة والكيماويات"},
        {"ticker": "EGCH.CA", "name": "المصرية للصناعات الكيماوية (إيجي كيم)"},
        {"ticker": "MBSC.CA", "name": "مصر بني سويف للأسمنت"},
        {"ticker": "ALUM.CA", "name": "العربية للألومنيوم"},
        {"ticker": "ECAP.CA", "name": "العز للسيراميك والبورسلين"},
        {"ticker": "PRCL.CA", "name": "العامة لمنتجات السيراميك والبورسلين"},
        {"ticker": "CERA.CA", "name": "العربية للسيراميك"},
        {"ticker": "MEGM.CA", "name": "الشرق الأوسط لصناعة الزجاج"},
        {"ticker": "KZPC.CA", "name": "كفر الزيات للمبيدات والكيماويات"},
        {"ticker": "ZEOT.CA", "name": "الزيوت المستخلصة ومشتقاتها"},
        {"ticker": "SMFR.CA", "name": "سماد مصر (إيجيفرت)"},
        {"ticker": "GDWA.CA", "name": "جدوى للتنمية الصناعية"},
        {"ticker": "NDRL.CA", "name": "الحفر الوطنية"},
        {"ticker": "RUBX.CA", "name": "روبكس إنترناشيونال لصناعة البلاستيك والأكريليك"},
        {"ticker": "EGAS.CA", "name": "مصر للغاز"},
        {"ticker": "ALEXA.CA", "name": "أسمنت الإسكندرية"},
        {"ticker": "DIFC.CA", "name": "الدولية للثلج الجاف"},
        {"ticker": "EDBM.CA", "name": "المصرية لتنمية مواد البناء"},
        {"ticker": "ICAL.CA", "name": "إنتر القاهرة لصناعة الألومنيوم"},
        {"ticker": "ICFC.CA", "name": "الدولية للأسمدة والكيماويات"},
        {"ticker": "IRAX.CA", "name": "العز الدخيلة للصلب - الإسكندرية"},
        {"ticker": "MISR.CA", "name": "مصر انتركونتيننتال للجرانيت والرخام"},
        {"ticker": "NCEM.CA", "name": "أسمنت المصرية الوطنية"},
        {"ticker": "PACH.CA", "name": "الدهانات والصناعات الكيماوية"},
        {"ticker": "SMCS.CA", "name": "سامكريت مصر"},
        {"ticker": "SMCSA.CA", "name": "سامكريت مصر (أسهم ممتازة)"},
        {"ticker": "SUCE.CA", "name": "أسمنت السويس"},
        {"ticker": "TORA.CA", "name": "أسمنت طرة"},
        {"ticker": "WATP.CA", "name": "الحديثة للعزل المائي"},
    ],
    "الصناعة والسلع المعمرة": [
        {"ticker": "SWDY.CA", "name": "السويدي إلكتريك"},
        {"ticker": "ORWE.CA", "name": "النساجون الشرقيون للسجاد"},
        {"ticker": "MICH.CA", "name": "مصر للصناعات الكيماوية"},
        {"ticker": "ACGC.CA", "name": "العربية لحلج الأقطان"},
        {"ticker": "KABO.CA", "name": "النصر للملابس والمنسوجات (كابو)"},
        {"ticker": "SPIN.CA", "name": "الإسكندرية للغزل والنسيج (سبينالكس)"},
        {"ticker": "UASG.CA", "name": "المتحدة للشحن والتفريغ"},
        {"ticker": "ELEC.CA", "name": "إليكتريك كابلات مصر"},
        {"ticker": "GTWL.CA", "name": "جولدن تكستايلز آند كلوثز وول"},
        {"ticker": "LCSW.CA", "name": "ليسيكو مصر"},
        {"ticker": "APSW.CA", "name": "يونيراب بولفارا للغزل والنسيج"},
        {"ticker": "AMII.CA", "name": "العربية للصناعات المعدنية والاستثمارات الصناعية"},
        {"ticker": "CFGH.CA", "name": "كونكريت فاشون جروب للاستثمارات التجارية والصناعية"},
        {"ticker": "EEII.CA", "name": "العربية للصناعات الهندسية"},
        {"ticker": "ACRO.CA", "name": "أكرو مصر (السقالات المعدنية)"},
        {"ticker": "ARVA.CA", "name": "العربية للصمامات"},
        {"ticker": "BIGP.CA", "name": "مجموعة الباربري للاستثمار"},
        {"ticker": "EBDP.CA", "name": "البدر للبلاستيك"},
        {"ticker": "INEE.CA", "name": "الصناعات الهندسية (إندس)"},
        {"ticker": "INEG.CA", "name": "المتكاملة للصناعات الهندسية"},
        {"ticker": "MBEN.CA", "name": "إم بي للهندسة"},
        {"ticker": "MRCO.CA", "name": "مصر للتبريد وتكييف الهواء"},
        {"ticker": "NASR.CA", "name": "النصر لتصنيع المحولات الكهربائية (الماكو)"},
        {"ticker": "NCGC.CA", "name": "النيل لحلج الأقطان"},
    ],
    "الأدوية والرعاية الصحية": [
        {"ticker": "PHAR.CA", "name": "إيبيكو (الشركة المصرية الدولية للصناعات الدوائية)"},
        {"ticker": "ISPH.CA", "name": "ابن سينا فارما"},
        {"ticker": "RMDA.CA", "name": "العاشر من رمضان للصناعات الدوائية (راميدا)"},
        {"ticker": "CLHO.CA", "name": "شركة مستشفى كليوباترا (CLHO)"},
        {"ticker": "AXPH.CA", "name": "الإسكندرية للأدوية والصناعات الكيماوية"},
        {"ticker": "NIPH.CA", "name": "النيل للأدوية والصناعات الكيماوية"},
        {"ticker": "SPMD.CA", "name": "سبيد ميديكال"},
        {"ticker": "MCRO.CA", "name": "ماكرو جروب للمستحضرات الطبية (ماكرو كابيتال)"},
        {"ticker": "MPCI.CA", "name": "ممفيس للأدوية والصناعات الكيماوية"},
        {"ticker": "BIOC.CA", "name": "جلاكسو سميث كلاين مصر"},
        {"ticker": "CPCI.CA", "name": "القاهرة للأدوية والصناعات الكيماوية"},
        {"ticker": "ADCI.CA", "name": "العربية للأدوية"},
        {"ticker": "OCPH.CA", "name": "أكتوبر فارما"},
        {"ticker": "MIPH.CA", "name": "مينافارم للصناعات الدوائية"},
        {"ticker": "SIPC.CA", "name": "سبأ الدولية للصناعات الدوائية والكيماوية"},
        {"ticker": "AMES.CA", "name": "الإسكندرية الطبي الجديد"},
        {"ticker": "NINH.CA", "name": "مستشفى النزهة الدولي"},
        {"ticker": "PHGC.CA", "name": "بريميوم للرعاية الصحية"},
        {"ticker": "AMEC.CA", "name": "أميكو للصناعات الطبية"},
        {"ticker": "ICMI.CA", "name": "الدولية للصناعات الطبية"},
        {"ticker": "IDHC.CA", "name": "المتكاملة للتشخيص القابضة"},
        {"ticker": "RIVA.CA", "name": "ريفا فارما"},
    ],
    "الاتصالات وتكنولوجيا المعلومات": [
        {"ticker": "ETEL.CA", "name": "المصرية للاتصالات (WE)"},
        {"ticker": "EGSA.CA", "name": "المصرية للأقمار الصناعية (نايل سات)"},
        {"ticker": "DGTZ.CA", "name": "ديجيتايز للاستثمار والتكنولوجيا"},
        {"ticker": "AMPI.CA", "name": "الموشر للبرمجة (نوفيدا للاستثمار التكنولوجي)"},
        {"ticker": "VERT.CA", "name": "فيرتيكا"},
        {"ticker": "ESAC.CA", "name": "مصر وجنوب أفريقيا للاتصالات"},
        {"ticker": "GTHE.CA", "name": "جلوبال تيليكوم القابضة"},
        {"ticker": "ITSY.CA", "name": "آي تي سينرجي"},
        {"ticker": "OREG.CA", "name": "أورانج مصر للاتصالات"},
        {"ticker": "OTMT.CA", "name": "أوراسكوم للاستثمار القابضة (تليكوم)"},
        {"ticker": "PTCC.CA", "name": "فرعون تك لأنظمة التحكم والاتصالات"},
        {"ticker": "VODE.CA", "name": "فودافون مصر"},
        {"ticker": "XPIN.CA", "name": "إكسبريس إنتجريشن"},
    ],
    "الأغذية والمشروبات والتبغ": [
        {"ticker": "SUGR.CA", "name": "الدلتا للسكر"},
        {"ticker": "CEFM.CA", "name": "مطاحن مصر الوسطى"},
        {"ticker": "MOSC.CA", "name": "مصر للزيوت والصابون"},
        {"ticker": "COSG.CA", "name": "القاهرة للزيوت والصابون"},
        {"ticker": "AFMC.CA", "name": "الإسكندرية لطحن الغلال"},
        {"ticker": "WCDF.CA", "name": "غرب ووسط الدلتا لطحن الغلال"},
        {"ticker": "EDFM.CA", "name": "شرق الدلتا لطحن الغلال"},
        {"ticker": "MILS.CA", "name": "شمال القاهرة لطحن الغلال"},
        {"ticker": "SCFM.CA", "name": "جنوب القاهرة والجيزة لطحن الغلال والمخابز"},
        {"ticker": "UEFM.CA", "name": "مطاحن مصر العليا"},
        {"ticker": "GSSC.CA", "name": "العامة للصوامع والتخزين"},
        {"ticker": "EAST.CA", "name": "إيسترن كومباني (الشرقية للدخان)"},
        {"ticker": "JUFO.CA", "name": "جهينة للصناعات الغذائية"},
        {"ticker": "DOMT.CA", "name": "الصناعات الغذائية العربية (دومتي)"},
        {"ticker": "EDITA.CA", "name": "إيديتا للصناعات الغذائية"},
        {"ticker": "SUGR.CA", "name": "الدلتا للسكر"},
        {"ticker": "DSCW.CA", "name": "دايس للملابس الجاهزة"},
        {"ticker": "POUL.CA", "name": "القاهرة للدواجن"},
        {"ticker": "ISMA.CA", "name": "الإسماعيلية مصر للدواجن"},
        {"ticker": "AJWA.CA", "name": "أجواء للصناعات الغذائية"},
        {"ticker": "OLFI.CA", "name": "عبور لاند للصناعات الغذائية"},
        {"ticker": "CEFM.CA", "name": "مطاحن مصر الوسطى"},
        {"ticker": "EFID.CA", "name": "إيديتا للصناعات الغذائية (بالدولار)"},
        {"ticker": "INFI.CA", "name": "الإسماعيلية الوطنية للصناعات الغذائية"},
        {"ticker": "MPCO.CA", "name": "المنصورة للدواجن"},
        {"ticker": "EPCO.CA", "name": "مصر للدواجن"},
        {"ticker": "ADPC.CA", "name": "العربية لمنتجات الألبان"},
        {"ticker": "MOSC.CA", "name": "مصر للزيوت والصابون"},
        {"ticker": "COSG.CA", "name": "القاهرة للزيوت والصابون"},
        {"ticker": "ALRA.CA", "name": "أطلس للاستثمار والصناعات الغذائية"},
        {"ticker": "SNFC.CA", "name": "الشرقية الوطنية للأمن الغذائي"},
        {"ticker": "GOUR.CA", "name": "جورميه إيجيبت للأغذية"},
        {"ticker": "AFMC.CA", "name": "الإسكندرية لطحن الغلال"},
        {"ticker": "WCDF.CA", "name": "غرب ووسط الدلتا لطحن الغلال"},
        {"ticker": "EDFM.CA", "name": "شرق الدلتا لطحن الغلال"},
        {"ticker": "MILS.CA", "name": "شمال القاهرة لطحن الغلال"},
        {"ticker": "SCFM.CA", "name": "جنوب القاهرة والجيزة لطحن الغلال والمخابز"},
        {"ticker": "UEFM.CA", "name": "مطاحن مصر العليا"},
        {"ticker": "GSSC.CA", "name": "العامة للصوامع والتخزين"},
        {"ticker": "ESGI.CA", "name": "المصرية للنشا والجلوكوز"},
        {"ticker": "MKIT.CA", "name": "مصر الكويت للاستثمار والتجارة (ميتيلو)"},
        {"ticker": "NCMP.CA", "name": "الوطنية لمنتجات الذرة"},
        {"ticker": "SNFI.CA", "name": "سوهاج الوطنية للصناعات الغذائية"},
        {"ticker": "UNFO.CA", "name": "يونيفرت للصناعات الغذائية"},
    ],
    "الخدمات والمنتجات الصناعية والسيارات": [
        {"ticker": "AMOC.CA", "name": "أموك (الإسكندرية للزيوت المعدنية)"},
        {"ticker": "ALCN.CA", "name": "الإسكندرية لتداول الحاويات والبضائع"},
        {"ticker": "AUTO.CA", "name": "جي بي كورب (غبور أوتو سابقاً)"},
        {"ticker": "TAQA.CA", "name": "طاقة عربية"},
        {"ticker": "RAYA.CA", "name": "راية القابضة للاستثمارات المالية"},
        {"ticker": "MOIL.CA", "name": "ماريديف (الخدمات الملاحية والبترولية)"},
        {"ticker": "CIRA.CA", "name": "سيرا للتعليم"},
        {"ticker": "MTIE.CA", "name": "إم إم جروب للصناعة والتجارة"},
        {"ticker": "RACC.CA", "name": "راية لخدمات مراكز الاتصالات"},
        {"ticker": "ETRS.CA", "name": "إيجيترانس (المصرية للنقل البحري)"},
        {"ticker": "CSAG.CA", "name": "قناة السويس لتوطين التكنولوجيا"},
        {"ticker": "MPRC.CA", "name": "مدينة الإنتاج الإعلامي"},
        {"ticker": "KORA.CA", "name": "كورة للطاقة والمشروعات الاستثمارية"},
        {"ticker": "DCCC.CA", "name": "دمياط لتداول الحاويات والبضائع"},
        {"ticker": "POCO.CA", "name": "بورسعيد للحاويات ومناولة البضائع"},
        {"ticker": "MFSC.CA", "name": "مصر فري شوبس (السوق الحرة)"}
    ],
    "السياحة والفنادق": [
        {"ticker": "MHOT.CA", "name": "مصر للفنادق"},
        {"ticker": "PHTV.CA", "name": "بيراميزا للفنادق والمنتجعات"},
        {"ticker": "SPHT.CA", "name": "الشمس بيراميدز للفنادق والمشروعات السياحية"},
        {"ticker": "SDTI.CA", "name": "شرم دريمز للاستثمار السياحي"},
        {"ticker": "ROTO.CA", "name": "رواد للسياحة"},
        {"ticker": "TRTO.CA", "name": "ترانس أوشنز للجولات السياحية"},
        {"ticker": "MMAT.CA", "name": "مرسى علم للتنمية السياحية"},
        {"ticker": "RTVC.CA", "name": "ريمكو للقرى السياحية والإنشاءات"},
        {"ticker": "MENA.CA", "name": "مينا للاستثمار السياحي والعقاري"},
        {"ticker": "AMER.CA", "name": "عامر جروب القابضة"},
        {"ticker": "EITP.CA", "name": "المصرية للمشروعات السياحية الدولية"},
        {"ticker": "GETO.CA", "name": "جينيال تورز"},
        {"ticker": "GOCO.CA", "name": "الساحل الذهبي"},
        {"ticker": "NCIS.CA", "name": "نيوكاسل للاستثمار الرياضي"},
        {"ticker": "ODHN.CA", "name": "أوراسكوم للتنمية القابضة (سويسرا)"},
        {"ticker": "RMTV.CA", "name": "رواد مصر للاستثمار السياحي"},
        {"ticker": "SLTD.CA", "name": "سكاي لايت للتنمية السياحية"},
        {"ticker": "TOUR.CA", "name": "التعمير السياحي"},
    ],
    "الزراعة واستصلاح الأراضي": [
        {"ticker": "IFAP.CA", "name": "الدولية للمحاصيل الزراعية"},
        {"ticker": "LUTS.CA", "name": "لوتس للاستثمارات الزراعية والتنمية"},
        {"ticker": "GGRN.CA", "name": "جو جرين للاستثمار الزراعي والتنمية"},
        {"ticker": "ELNA.CA", "name": "النصر لتصنيع المحاصيل الزراعية"},
        {"ticker": "KRDI.CA", "name": "الخير ريفر للتنمية الزراعية والاستثمار البيئي"},
        {"ticker": "AALR.CA", "name": "العامة لاستصلاح الأراضي والتنمية والتعمير"},
        {"ticker": "EALR.CA", "name": "العربية لاستصلاح الأراضي"},
        {"ticker": "WKOL.CA", "name": "وادي كوم أمبو لاستصلاح الأراضي"},
        {"ticker": "NEDA.CA", "name": "الوجه القبلي الشمالي للتنمية والإنتاج الزراعي"},
        {"ticker": "PSAD.CA", "name": "بورسعيد للتنمية الزراعية والإنشاءات"}
    ],
    "التعليم": [
        {"ticker": "TALM.CA", "name": "تعليم لإدارة الخدمات التعليمية"},
        {"ticker": "CAED.CA", "name": "القاهرة للخدمات التعليمية"},
        {"ticker": "MOED.CA", "name": "المصرية الحديثة للتعليم"}
    ],
    "الطباعة والتغليف والورق": [
        {"ticker": "UNIP.CA", "name": "يونيفرسال للورق ومواد التغليف"},
        {"ticker": "RAKT.CA", "name": "راكتا لصناعة الورق"},
        {"ticker": "NAPR.CA", "name": "المصرية الوطنية للطباعة"},
        {"ticker": "DTPP.CA", "name": "دلتا للطباعة والتغليف"},
        {"ticker": "EPPK.CA", "name": "الأهرام للطباعة والتغليف"},
        {"ticker": "MEPA.CA", "name": "التعبئة والتغليف الطبي"},
        {"ticker": "APPC.CA", "name": "المتقدمة للتعبئة والتغليف الدوائي"},
        {"ticker": "IPPM.CA", "name": "الدولية لمواد الطباعة والتغليف"},
        {"ticker": "SBAG.CA", "name": "السويس لصناعة الأكياس"},
        {"ticker": "SIMO.CA", "name": "مصر الشرق الأوسط للورق (سيمو)"},
        {"ticker": "SMPP.CA", "name": "الشروق للطباعة والتغليف الحديثة"},
        {"ticker": "TECH.CA", "name": "تغليف إندستريز - مصر"},
    ]
}

_EXPLICIT_TICKER_SECTORS = {
    "الأنشطة المالية المتنوعة": ["EKHO", "EKHOA", "OIH", "AFDI", "ELWA", "GDWA", "KWIN", "ABRD", "AGIN", "AIND", "AITG", "AIVCB", "AMIA", "ANFI", "BCAP", "CCAP", "CCAPP", "CIRF", "GRCA", "ICID", "IBCT", "LKGP", "MAAL", "MEDA", "MFINEG", "NCIN", "ODID", "REAC", "SEIG", "SEIGA", "SRWA", "ACAP", "ASPI", "AIHC", "BINV", "GMCI", "GTEX", "AIDC", "BIGP"],
    "استثمار وتمويل وائتمان": ["ACTF", "ATLC", "CNFN", "CPME", "ICLE", "NAHO", "PRMH", "VALU", "VLMRA", "TYCN"],
    "وساطة وإدارة أصول": ["ACAMD", "EASB", "EBSC", "EOSB", "ICFC", "ODIN"],
    "فنادق": ["MHOT", "PHTV", "SPHT", "TOUR"],
    "تطوير سياحي وترفيهي": ["EGTS", "RREI", "UTOP", "SDTI", "ROTO", "TRTO", "MMAT", "RTVC", "MENA", "AMER", "EITP", "GETO", "GOCO", "NCIS", "ODHN", "RMTV", "SLTD"],
    "دواجن وثروة حيوانية": ["POUL", "ISMA", "MPCO", "EPCO"],
    "أغذية ومشروبات": ["JUFO", "DOMT", "EDITA", "OLFI", "EFID", "INFI", "ADPC", "GOUR", "ESGI", "MKIT", "NCMP", "SNFI", "UNFO"],
    "اتصالات": ["ETEL", "GTHE", "OREG", "VODE"],
    "إعلام وأقمار صناعية": ["EGSA", "MPRC"],
    "استثمارات عقارية وغذائية": ["BSFR"],
    "أغذية واستثمارات غذائية": ["AJWA", "ALRA", "SNFC"],
    "كيماويات وأسمدة وبتروكيماويات": ["SMFR", "DIFC"],
    "تجارة تجزئة وسوق حرة": ["MFSC"],
    "التعليم": ["TALM", "CAED", "MOED", "CIRA"],
}
_explicit_sector_map = {
    ticker: sector
    for sector, tickers in _EXPLICIT_TICKER_SECTORS.items()
    for ticker in tickers
}
_unclassified_sectors = {}
for _old_sector, _companies in EGX_MARKET_BY_SECTOR.items():
    for _company in _companies:
        _symbol = _company["ticker"].removesuffix(".CA")
        _new_sector = _explicit_sector_map.get(_symbol)
        if _new_sector:
            _unclassified_sectors.setdefault(_new_sector, []).append(_company)
        else:
            _unclassified_sectors.setdefault(_old_sector, []).append(_company)
EGX_MARKET_BY_SECTOR = {
    sector: companies for sector, companies in _unclassified_sectors.items() if companies
}

# تقسيم فرعي أوضح للأنشطة المتخصصة، بدلاً من جمعها في قطاعات عريضة فقط.
# القوائم أدناه مبنية على نشاط الشركات المدوّن في أسماء الشركات داخل هذا الملف.
_SECTOR_RECLASSIFICATIONS = {
    "أسمنت": ["ASCM", "ARCC", "SVCE", "SCEM", "MCQE", "MBSC", "ALEXA", "NCEM", "SUCE", "TORA"],
    "مواد بناء وسيراميك وزجاج": ["EDBM", "ECAP", "PRCL", "CERA", "LCSW", "WATP", "MISR", "MEGM"],
    "معادن وحديد وألومنيوم": [
        "ESRS", "EGAL", "ATQA", "IRON", "ISMQ", "ALUM", "ICAL", "IRAX", "AMII",
    ],
    "كيماويات وأسمدة وبتروكيماويات": [
        "MFPC", "ABUK", "SKPC", "KIMA", "EFIC", "FERC", "EGCH", "KZPC", "ICFC", "PACH", "MICH", "SMFR", "DIFC",
    ],
    "أدوية وتصنيع دوائي": [
        "PHAR", "RMDA", "AXPH", "NIPH", "MPCI", "BIOC", "CPCI", "ADCI", "OCPH", "MIPH", "SIPC", "RIVA",
    ],
    "مستشفيات ورعاية صحية": [
        "CLHO", "SPMD", "AMES", "NINH", "PHGC", "IDHC",
    ],
    "مستلزمات وأجهزة طبية": ["AMEC", "ICMI"],
    "توزيع أدوية": ["ISPH"],
    "مستحضرات طبية وتجميل": ["MCRO"],
    "نسيج وملابس": ["DSCW", "ACGC", "KABO", "SPIN", "GTWL", "APSW", "CFGH", "ORWE", "NCGC"],
    "سيارات ومعدات نقل": ["AUTO", "GBCO"],
    "طاقة وخدمات بترولية": ["AMOC", "TAQA", "MOIL", "KORA", "EGAS", "NDRL"],
    "نقل وشحن ولوجستيات": ["ALCN", "UASG", "ETRS", "DCCC", "POCO"],
    "تصنيع ومعدات كهربائية": ["SWDY", "ELEC", "EEII", "ARVA", "EBDP", "INEE", "INEG", "MBEN", "MRCO", "NASR", "ACRO"],
    "تكنولوجيا وخدمات أعمال": ["RAYA", "RACC", "MTIE", "DGTZ", "VERT", "ESAC", "ITSY", "PTCC", "XPIN", "AMPI", "CSAG"],
    "اتصالات وإعلام": ["OTMT"],
    "عقارات وتطوير عمراني": [
        "TMGH", "PHDC", "OCDI", "MNHD", "HELI", "EMFD", "ORHD", "PRDC", "UNIT", "ELSH", "ARAB",
        "ZMID", "EHDR", "GPPL", "MASR", "BONY", "ELKA", "NARE", "GPIM", "IDRE", "NHPS", "OBRI",
        "TANM", "AREH", "CCRS", "GIHD", "COPR", "AREHA", "EIUD", "FIRED", "NOAF", "OCIC", "MENA",
    ],
    "مقاولات وإنشاءات": ["ORAS", "NCCW", "GGCC", "CRST", "UEGC", "ENGC", "DCRC", "FNAR", "SMCS", "SMCSA", "DAPH"],
    "سياحة وفنادق وترفيه": ["AMER"],
    "زراعة ومدخلات إنتاج": ["IFAP", "LUTS", "GGRN", "ELNA", "KRDI", "AALR", "EALR", "WKOL", "NEDA", "PSAD"],
    "زيوت وسكر وطحن وتخزين حبوب": ["ZEOT", "SUGR", "CEFM", "MOSC", "COSG", "AFMC", "WCDF", "EDFM", "MILS", "SCFM", "UEFM", "GSSC"],
    "تبغ": ["EAST"],
    "بلاستيك ومطاط": ["RUBX"],
}

_ticker_destinations = {
    ticker: sector
    for sector, tickers in _SECTOR_RECLASSIFICATIONS.items()
    for ticker in tickers
}
_reclassified_sectors = {sector: [] for sector in _SECTOR_RECLASSIFICATIONS}
_existing_sectors = {}
_seen_tickers = set()
for _old_sector, _companies in EGX_MARKET_BY_SECTOR.items():
    for _company in _companies:
        _ticker = _company["ticker"]
        _symbol = _ticker.removesuffix(".CA")
        if _ticker in _seen_tickers:
            continue
        _seen_tickers.add(_ticker)
        _destination = _ticker_destinations.get(_symbol)
        if _destination:
            _reclassified_sectors[_destination].append(_company)
        else:
            _existing_sectors.setdefault(_old_sector, []).append(_company)

EGX_MARKET_BY_SECTOR = {
    **{sector: companies for sector, companies in _existing_sectors.items() if companies},
    **{sector: companies for sector, companies in _reclassified_sectors.items() if companies},
}

# مرجع النطاق النشط في صفحة Stock Analysis لقائمة EGX، تمت مراجعته في 2026-10-05.
# الصفحة تصف القائمة بأنها أسهم متداولة بنشاط وتحدّثها يومياً؛ لذلك نستبعد هنا الرموز
# التي بقيت في القوائم القديمة لكنها لم تعد ضمن نطاق التداول النشط. إعادة المراجعة الدورية
# ضرورية لأن الإدراجات والإيقافات تتغير. هذا لا يغني عن قائمة EGX الرسمية عند تحديث الملف.
_ACTIVE_EGX_TICKERS = set("""
COMI SWDY ETEL TMGH EGAL MFPC QNBE HDBK ABUK ALCN ORAS EAST EFIH ADIB EMFD FWRY
SCTS CANA ORHD GPPL VLMR VLMRA EFID JUFO PHDC GBCO HRHO OCDI FAIT FAITA FERC BTFH
CIEB HELI EXPA BIOC RAYA EGCH CCAP IRON ARCC VALU TAQA CLHO SCEM CIRA PHAR ORWE MTIE
POUL SKPC MCQE AMOC EGTS MOIL SAUD UBEE EGSA EFIC NIPH MASR MBSC TALM EGBE MHOT KORA
ATQA BINV ISPH CICH AMES RMDA CSAG NAPR OIH AMIA IFAP MIPH MPRC MOIN CPCI PRDC OLFI
ISMQ EGAS PHTV MPCI SUGR ZMID AXPH BONY DOMT GOUR SPHT ELEC SPIN ARAB NINH ACAP ENGC
OCPH MCRO AFMC MICH KABO CNFN SVCE WCDF GSSC DSCW SDTI SAIB MFSC OFH ACGC AMER UNIT
KZPC GDWA AJWA UEFM CRST ADCI ELKA ACTF GPIM ASCM CFGH ELSH LCSW ALRA NAHO ICFC INFI
ZEOT ACAMD MPCO ETRS ATLC GTWL ISMA EDFM MAAL DAPH SMFR NARE CEFM PHGC MILS IDRE SNFC
NCCW GGRN ICID RACC ADPC EALR MOSC KRDI EHDR WKOL AALR DTPP ECAP MENA CERA ODIN GGCC
SCFM CAED ASPI MBEG DEIN PRCL SIPC LUTS NDRL IEEC NHPS MEPA AIHC SEIG SEIGA UEGC ALUM
AIDC GTEX OBRI TANM COSG POCO RREI EBSC RUBX AFDI RTVC TWSA AMII PRMH UNIP ICLE MEGM
APSW EASB ROTO MOED TYCN SPMD RAKT KWIN EEII AREH CCRS FCMD EPCO GRCA GIHD MMAT TRTO
ELNA ELWA DGTZ DCCC NEDA EPPK GMCI EOSB CPME COPR
""".split())

# رموز نشطة ظهرت في المرجع أعلاه ولم تكن ضمن القائمة المحلية السابقة.
_NEW_ACTIVE_EGX_STOCKS = [
    ("VLMR", "فالمور القابضة للاستثمار (السهم العادي)"),
    ("SCTS", "شركة قناة السويس لتوطين التكنولوجيا"),
    ("MBEG", "إم بي للهندسة والمقاولات"),
    ("IEEC", "الصناعات الهندسية والمشروعات"),
    ("FCMD", "الدولية للصناعات الطبية"),
    ("TWSA", "توسع للتخصيم"),
]
for _ticker, _name in _NEW_ACTIVE_EGX_STOCKS:
    if _ticker == "VLMR" or _ticker == "TWSA":
        _sector = "استثمار وتمويل وائتمان"
    elif _ticker == "SCTS":
        _sector = "تكنولوجيا وخدمات أعمال"
    elif _ticker == "FCMD":
        _sector = "مستلزمات وأجهزة طبية"
    else:
        _sector = "مقاولات وإنشاءات"
    EGX_MARKET_BY_SECTOR.setdefault(_sector, []).append(
        {"ticker": f"{_ticker}.CA", "name": _name}
    )

EGX_MARKET_BY_SECTOR = {
    _sector: [item for item in _items
              if item["ticker"].removesuffix(".CA") in _ACTIVE_EGX_TICKERS]
    for _sector, _items in EGX_MARKET_BY_SECTOR.items()
    if any(item["ticker"].removesuffix(".CA") in _ACTIVE_EGX_TICKERS for item in _items)
}

ISIN_BACKUP_MAP = {
    "ACTF.CA": "EGS7D5P1C019.CA",
    "TAQA.CA": "EGS490S1C014.CA",
    "AUTO.CA": "EGS04041C013.CA",
    "OLFI.CA": "EGS30281C010.CA",
    "EDITA.CA": "EGS30441C014.CA",
    "DOMT.CA": "EGS30341C018.CA",
    "RMDA.CA": "EGS3D3Y1C013.CA",
    "CLHO.CA": "EGS729J1C018.CA",
    "VLMRA.CA": "EGS69081C023.CA",
    "EFIH.CA": "EGS693M1C012.CA",
    "FWRY.CA": "EGS737M1C016.CA",
    "PHDC.CA": "EGS65341C014.CA",
    "TMGH.CA": "EGS65621C018.CA",
    "SWDY.CA": "EGS39011C019.CA",
    "SKPC.CA": "EGS38211C013.CA",
    "ABUK.CA": "EGS38111C014.CA",
    "MFPC.CA": "EGS38321C010.CA",
    "ESRS.CA": "EGS10711C010.CA",
    "HRHO.CA": "EGS690N1C015.CA",
    "COMI.CA": "EGS76001C010.CA",
    "ADIB.CA": "EGS60131C013.CA",
    "CICH.CA": "EGS69131C017.CA",
    "BTFH.CA": "EGS69221C016.CA",
    "OCDI.CA": "EGS65531C019.CA",
    "MNHD.CA": "EGS65541C018.CA",
    "JUFO.CA": "EGS30141C014.CA",
    "ETEL.CA": "EGS48031C019.CA",
    "EAST.CA": "EGS33011C018.CA"
}

# إعدادات الأطر الزمنية (Timeframe / Resolution)
# التجميع لـ "ساعتين" و "4 ساعات" مش متاح مباشرة من يوتفاينانس، فبيتم تجميعه (Resample)
# من بيانات الساعة (1h) نفسها بعد تحميلها مرة واحدة فقط (ومكاشة عشان السرعة).
TIMEFRAME_CONFIG = {
    "يومي":       {"interval": "1d",  "period": "2y",   "resample": None},
    "أسبوعي":     {"interval": "1wk", "period": "3y",   "resample": None},
    "4 ساعات":    {"interval": "1h",  "period": "60d",  "resample": "4h"},
    "ساعتين":     {"interval": "1h",  "period": "60d",  "resample": "2h"},
    "ساعة":       {"interval": "1h",  "period": "60d",  "resample": None},
    "ربع ساعة":   {"interval": "15m", "period": "20d",  "resample": None},
}
