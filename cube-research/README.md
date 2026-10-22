# بحث طرق حل مكعب روبيك 3×3 للإنسان

مشروع بحث وتطوير تجريبي: هل يمكن إيجاد طريقة (أو تحسين/تركيب) أسرع للإنسان، أسهل تعلّماً، وأقل حركات؟
التعريفات والمقاييس في [RESEARCH_GOAL.md](RESEARCH_GOAL.md). **الوضع الحالي للادعاءات في [CLAIMS.md](CLAIMS.md).**

## التشغيل

```bash
pip install kociemba pytest          # kociemba = مرجع خارجي مستقل (اختياري لكنه مستخدم في الاختبارات)
cd cube-research
python3 -m pytest -q                 # اختبارات الصحة (أول تشغيل يبني جداول ~1-3 دقائق)
python3 server.py                    # المختبر: افتح http://127.0.0.1:8765/
python3 experiments/e01_htr_group.py
python3 experiments/e02_method_baselines.py 50 dev
python3 experiments/e03_ll_library.py
```

تُبنى الجداول تلقائياً في `data/tables/` (~1.2 GB، غير مرفوعة في git). مكتبة C تُترجم تلقائياً إلى `build/`.

## البنية

| المسار | المحتوى |
|---|---|
| `src/cuberesearch/cubie.py` | نموذج القطع (تعريفات Kociemba)، التحقق من الصلاحية، تحويل الملصقات |
| `src/cuberesearch/notation.py` | الرموز (أوجه، شرائح، واسعة، تدوير) والمقاييس HTM/QTM/STM/ETM/ATM |
| `src/cuberesearch/sticker.py` | نموذج ملصقات هندسي **مستقل** للتحقق المتقاطع |
| `csrc/core.c` + `src/cuberesearch/core.py` | محرك بحث C: محلّل أمثل (Korf IDA*) + جداول أنماط + IDA* للخطوات |
| `src/cuberesearch/methods.py` | الطرق كسلاسل أهداف وسيطة قابلة للبرمجة: CFOP, ZZ, Petrus, Roux, EO→DR→HTR |
| `src/cuberesearch/ll.py` | زمرة الطبقة الأخيرة الكاملة (62,208 حالة) وعدّ الحالات ومسافات «المكتبة» |
| `src/cuberesearch/ergo.py` | نموذج جهد تنفيذ **تقديري غير معايَر** مع تحليل حساسية |
| `src/cuberesearch/datasets.py` | مجموعات dev/tune/test ببذور ثابتة (حالات موحّدة التوزيع) |
| `experiments/` | سكربتات التجارب (كل واحدة تحفظ provenance) |
| `results/` | النتائج الخام JSON والسجلات |
| `web/` + `server.py` | المختبر التفاعلي بالعربية (محلي فقط) |
| `tests/` | اختبارات الصحة |

## وثائق البحث
[RESEARCH_GOAL](RESEARCH_GOAL.md) · [PRIOR_ART](PRIOR_ART.md) · [HYPOTHESES](HYPOTHESES.md) · [DECISIONS](DECISIONS.md) ·
[EXPERIMENT_LOG](EXPERIMENT_LOG.md) · [CLAIMS](CLAIMS.md) · [NEXT_STEPS](NEXT_STEPS.md)

## مكتبات خارجية
- `kociemba` (PyPI، تنفيذ C لخوارزمية Kociemba): مرجع مستقل للتحقق ولتوليد خلطات تنتج حالات موحّدة. ليست اختراعنا.
- لا مكتبات أخرى. محرك البحث (Korf IDA* + pattern databases) تنفيذنا لفكرة منشورة (Korf 1997).
