# الأعمال السابقة والحدود المعروفة

تاريخ التحقق: 2026-10-22. مستوى الثقة لكل سطر مذكور. **speedsolving.com يرفض الجلب المباشر (403) من هذه البيئة**،
لذا أرقام الويكي هناك مأخوذة من مقتطفات محركات البحث وموسومة «غير مؤكد مباشرة».

## 1. حدود رياضية (حقائق موثّقة)

| الحقيقة | القيمة | المصدر | تحقّقنا بأنفسنا؟ |
|---|---|---|---|
| عدد حالات المكعب | 43,252,003,274,489,856,000 | معروف (8!·3^7·12!·2^11/2) | الصيغة مطبّقة في `random_state` |
| God's number HTM | 20 (2010) | [cube20.org](https://cube20.org/) | لا (يتطلب 35 سنة-معالج) |
| God's number QTM | 26 (2014) | [cube20.org/qtm](https://cube20.org/qtm/) | لا |
| زمرة أنصاف اللفات G3=<U2,D2,R2,L2,F2,B2> | 663,552 حالة، أقصى بعد 15 بأنصاف لفات فقط | [Jaap's Thistlethwaite page](https://www.jaapsch.net/puzzles/thistle.htm)، [OEIS A080627](https://oeis.org/A080627) | **نعم، بحث شامل (E01)** |
| من HTR إلى الحل بكل الحركات | ≤13 HTM حسب ويكي speedsolving (غير مؤكد مباشرة) | [speedsolving HTR](https://www.speedsolving.com/wiki/index.php?title=HTR) | جزئياً (E01: كل حالات العمق 15 + عينة) |
| من DR إلى الحل | ≤12 HTM حسب ويكي speedsolving (غير مؤكد مباشرة) | [speedsolving DR](https://www.speedsolving.com/wiki/index.php?title=DR) | لا بعد |
| توزيع Cross الأمثل (HTM) | 0:1, 1:15, 2:158, 3:1394, 4:9809, 5:46381, 6:97254, 7:34966, 8:102 (متوسط 5.81) | رقم شائع في المجتمع | **نعم، شامل (اختبار `test_core`)** |
| Korf 1997: IDA* + pattern databases، وسيط الحل الأمثل ≈18 | | [Korf AAAI 1997](https://www.cs.princeton.edu/courses/archive/fall06/cos402/papers/korfrubik.pdf) | نستخدم نفس الفكرة |

## 2. الطرق البشرية

| الطريقة | الفكرة الأساسية | ما تحسّنه | القيود | الحفظ/التعرّف | الحركات المذكورة (المقياس) | المصدر | علاقتها بنا |
|---|---|---|---|---|---|---|---|
| CFOP | Cross ثم 4 أزواج F2L ثم OLL ثم PLL | تعرّف بسيط، تنفيذ سريع، تدوير قليل الحسابات | حركات أكثر، تدويرات y | 78 خوارزمية لـ 2LLL (57+21) | ~57.5 (ويكي، غالباً STM، غير مؤكد) ؛ ~54 (ورقة طلابية) | [speedsolving CFOP](https://www.speedsolving.com/wiki/index.php?title=CFOP)، [emerginginvestigators](https://emerginginvestigators.org/articles/21-189/pdf) | مرجع أساسي؛ نمذجناه (E02) |
| Roux | كتلتان 1×2×3 ثم CMLL ثم LSE بحركات M,U | حركات أقل، بلا تدوير | حركات M أصعب لبعض الناس، تخطيط كتل حدسي | 42 CMLL (متوسط 10.95 HTM لمجموعة Kian حسب الويكي) | ~48 STM | [ruwix Roux](https://ruwix.com/the-rubiks-cube/different-rubiks-cube-solving-methods/roux-method/) | نمذجناه |
| ZZ | EOLine ثم F2L بـ<R,U,L> ثم LL | لا تدوير، LL أسهل لأن الحواف موجّهة | EOLine صعب في الفحص | OCLL+PLL (28) أو ZBLL (493) | «أقل قليلاً من CFOP» | ويكي CFOP/ZZ (غير مؤكد) | نمذجناه |
| Petrus | 2×2×2 → 2×2×3 → EO → F2L بـ<R,U> → LL | حركات قليلة | تخطيط كتل صعب بسرعة | كما ZZ | مذكور أقل من أغلب الطرق (ادعاء في الويكي) | [forum](https://www.speedsolving.com/threads/asking-chatgpt-cubing-stuff.94016/page-2) | نمذجناه |
| Thistlethwaite (حاسوبي/FMC) | سلسلة زمر G0→G1(EO)→G2(DR)→G3(HTR)→حل | حد أعلى مضمون 52 | غير عملي للسرعة | — | ≤52 HTM | [Jaap](https://www.jaapsch.net/puzzles/thistle.htm) | E01 يتحقق من خصائص G3 |
| Kociemba Two-Phase | G1 = DR ثم حل داخل G1 مع تحسين مستمر | حلول ~19-20 HTM بسرعة | حاسوبي فقط | — | <19 متوسط (وصف الحزمة) | حزمة `kociemba` / `RubikTwoPhase` | **مرجعنا الحاسوبي المستقل** |
| FMC (EO/DR/HTR + NISS + insertions) | تقليل حركات بشري بلا حدود زمنية قاسية (60 دقيقة) | أقل حركات بشرية (~25-30) | بطيء جداً للسرعة | خبرة عالية | ~28 لـ Roux-FMC (ruwix)، أفضل البشر أقل | [nissy-classic](https://github.com/sebastianotronto/nissy-classic) | نعيد إنتاج خطواته حسابياً |

### تقنيات «التأثير» على الخطوة التالية (مرتبطة بـ H8)
- CMLL+EO (اسمها الأول KCLL ثم CLLEO، Thom Barlow): حفظ عدة خوارزميات لكل حالة CMLL تختلف في أثرها على توجيه الحواف لتسهيل LSE.
- EOLR / EOLRb: توجيه الحواف مع وضع UL/UR. Pinkie Pie (Rob Stuart 2011، Alex Lau 2012). المصدر: [speedsolving CMLL](https://www.speedsolving.com/wiki/index.php/CMLL) (عبر مقتطف البحث).
- لم أجد مصدراً يقيس كمياً «كم حركة توفّر كل خوارزمية إضافية» — هذا ما يضيفه E09 (قياس لا اختراع).

## 3. أدوات وأبحاث حاسوبية

| العمل | الفكرة | علاقته |
|---|---|---|
| Korf 1997 | IDA* + PDB | استخدمناه لمحلّل أمثل (`csrc/core.c`) |
| Rokicki et al. (cube20) | cosets + تناظر | حدود نظرية فقط |
| DeepCubeA (Agostinelli 2019) | تعلّم معزز + A* موزون | حلول ~20 حركة، استراتيجية «غير بشرية» حسب مؤلفيه ([techxplore](https://techxplore.com/news/2019-07-deep-algorithm-rubik-cube-faster.html)) |
| ALLURE / Explainable pathfinding (Agostinelli وآخرون، AAAI 2022 / ICAPS 2022 workshop) | اكتشاف رسم بياني من **أهداف فرعية مفهومة** بالبرمجة المنطقية الاستقرائية | **أقرب عمل سابق لفكرة «الشكل الوسيط»**؛ هدفه التعليم لا السرعة ([arXiv 2511.01683](https://arxiv.org/pdf/2511.01683)، [AAAI demo](https://ojs.aaai.org/index.php/AAAI/article/view/21722)) |
| nissy (Tronto) | محلّل FMC يدعم EO/DR/HTR وNISS | لم نستخدمه (نكتب أدواتنا) |

## 4. نماذج زمن التنفيذ البشري
لم أجد ورقة محكّمة تقدّم نموذجاً مُعايَراً لزمن تنفيذ الخوارزميات بالأصابع (بحث موسّع بتاريخ 2026-10-22).
توجد معرفة مجتمعية (fingertricks، regrips، «speed-optimal algs») لكن بلا نموذج مفتوح موثّق وجدته.
أدوات مجتمعية مثل مقدّرات سرعة الخوارزميات قد تكون موجودة لكنني **لم أتحقق منها**، فلا أعتمد عليها.
⇒ أي نموذج ergonomic عندنا «تقدير غير معايَر».

## 5. أرقام قياسية (للسياق فقط، غير مستخدمة كدليل على طرق)
موقع WCA الرسمي للأرقام رفض الجلب (403). مصادر ثانوية (ruwix، Wikipedia) تذكر 2.51 ث فردي (Xuanyi Geng، أكتوبر 2026)
و3.51 ث متوسط (Yiheng Wang، يونيو 2026). **غير مؤكد من المصدر الرسمي.** الرقم الفردي لا يدل على متوسط أداء طريقة.

## 6. قواعد WCA ذات الصلة (مؤكدة من النص الرسمي، نسخة 2026-04-01)
- A3a1: وقت فحص أقل من 15 ث. A4d1: بدء بعد 15 ث → +2. A4d2: بعد 17 ث → DNF.
