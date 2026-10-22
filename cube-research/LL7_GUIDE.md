# دليل الطبقة الأخيرة بسبع خوارزميات (مولَّد آلياً ومتحقَّق منه)

امسك المكعب واللون العلوي (لون مركز U) فوق. الرسم منظر من الأعلى والوجه الأمامي في الأسفل:
المربع 3×3 في الوسط هو الوجه العلوي؛ الصف الأعلى = الحافة العليا للوجه الخلفي، العمود الأيسر = الوجه الأيسر، الأيمن = الأيمن، الصف الأسفل = الوجه الأمامي.
في المرحلتين 1–2: `X` = ملصق بلون الوجه العلوي، `.` = غير ذلك. في 3–4: الحرف = لون الملصق باسم وجهه الأصلي (R,F,L,B).

## الخوارزميات السبع

- **EO-A**: `F R U R' U' F'` (6 STM) — 1) توجيه حواف الطبقة العليا (EO)
- **EO-B**: `F U R U' R' F'` (6 STM) — 1) توجيه حواف الطبقة العليا (EO)
- **Sune**: `R U R' U R U2 R'` (7 STM) — 2) توجيه الأركان (CO)
- **AntiSune**: `R U2 R' U' R U' R'` (7 STM) — 2) توجيه الأركان (CO)
- **Aa**: `R' F R' B2 R F' R' B2 R2` (9 STM) — 3) ترتيب الأركان (CP)
- **Ua**: `R U' R U R U R U' R' U' R2` (11 STM) — 4) ترتيب الحواف وإنهاء الحل (EP)
- **Ub**: `R2 U R U R' U' R' U' R' U R'` (11 STM) — 4) ترتيب الحواف وإنهاء الحل (EP)

## 1) توجيه حواف الطبقة العليا (EO)

### احتمال 50.0% — 6 STM — `EO-B`

```
  . . .  
. X X X .
. X X . X
. X . X .
  . X .  
```
الحركات: `F U R U' R' F'`

### احتمال 25.0% — 6 STM — `EO-A`

```
  . X .  
. X . X .
. X X X .
. X . X .
  . X .  
```
الحركات: `F R U R' U' F'`

### احتمال 12.5% — 13 STM — `EO-A U2 EO-B`

```
  . X .  
. X . X .
X . X . X
. X . X .
  . X .  
```
الحركات: `F R U R' U' F' U2 F U R U' R' F'`

## 2) توجيه الأركان (CO)

### احتمال 14.8% — 7 STM — `AntiSune`

```
  . . .  
X . X X .
. X X X .
. . X . X
  X . .  
```
الحركات: `R U2 R' U' R U' R'`

### احتمال 14.8% — 7 STM — `Sune`

```
  X . .  
. . X . X
. X X X .
. X X . .
  . . X  
```
الحركات: `R U R' U R U2 R'`

### احتمال 14.8% — 15 STM — `AntiSune U Sune`

```
  . . .  
X . X . X
. X X X .
. X X X .
  . . .  
```
الحركات: `R U2 R' U' R U' R' U R U R' U R U2 R'`

### احتمال 14.8% — 15 STM — `Sune U2 AntiSune`

```
  . . .  
. X X . X
. X X X .
. . X X .
  X . .  
```
الحركات: `R U R' U R U2 R' U2 R U2 R' U' R U' R'`

### احتمال 14.8% — 15 STM — `Sune U' Sune`

```
  . . X  
X . X . .
. X X X .
X . X . .
  . . X  
```
الحركات: `R U R' U R U2 R' U' R U R' U R U2 R'`

### احتمال 14.8% — 15 STM — `AntiSune U' Sune`

```
  . . .  
. X X . X
. X X X .
. X X . X
  . . .  
```
الحركات: `R U2 R' U' R U' R' U' R U R' U R U2 R'`

### احتمال 7.4% — 14 STM — `Sune Sune`

```
  . . .  
X . X . X
. X X X .
X . X . X
  . . .  
```
الحركات: `R U R' U R U2 R' R U R' U R U2 R'`

## 3) ترتيب الأركان (CP)

### احتمال 16.7% — 9 STM — `Aa`

```
  L B L  
F X X X B
L X X X R
R X X X R
  B F F  
```
الحركات: `R' F R' B2 R F' R' B2 R2`

### احتمال 16.7% — 9 STM — `Aa`

```
  B L B  
L X X X R
F X X X B
F X X X F
  R R L  
```
الحركات: `R' F R' B2 R F' R' B2 R2`

### احتمال 16.7% — 9 STM — `Aa`

```
  R R R  
B X X X F
L X X X F
L X X X L
  F B B  
```
الحركات: `R' F R' B2 R F' R' B2 R2`

### احتمال 16.7% — 9 STM — `Aa`

```
  F F F  
R X X X L
R X X X B
B X X X B
  L L R  
```
الحركات: `R' F R' B2 R F' R' B2 R2`

### احتمال 16.7% — 19 STM — `Aa U Aa`

```
  B L F  
L X X X L
B X X X R
R X X X R
  B F F  
```
الحركات: `R' F R' B2 R F' R' B2 R2 U R' F R' B2 R F' R' B2 R2`

## 4) ترتيب الحواف وإنهاء الحل (EP)

### احتمال 8.3% — 11 STM — `Ub`

```
  B B B  
L X X X R
R X X X F
L X X X R
  F L F  
```
الحركات: `R2 U R U R' U' R' U' R' U R'`

### احتمال 8.3% — 11 STM — `Ua`

```
  B B B  
L X X X R
F X X X L
L X X X R
  F R F  
```
الحركات: `R U' R U R U R U' R' U' R2`

### احتمال 8.3% — 12 STM — `Ub U`

```
  R R R  
B X X X F
F X X X L
B X X X F
  L B L  
```
الحركات: `R2 U R U R' U' R' U' R' U R' U`

### احتمال 8.3% — 12 STM — `Ua U`

```
  R R R  
B X X X F
L X X X B
B X X X F
  L F L  
```
الحركات: `R U' R U R U R U' R' U' R2 U`

### احتمال 8.3% — 12 STM — `Ua U2`

```
  F F F  
R X X X L
B X X X R
R X X X L
  B L B  
```
الحركات: `R U' R U R U R U' R' U' R2 U2`

### احتمال 8.3% — 12 STM — `Ub U2`

```
  F F F  
R X X X L
L X X X B
R X X X L
  B R B  
```
الحركات: `R2 U R U R' U' R' U' R' U R' U2`

### احتمال 8.3% — 12 STM — `Ub U'`

```
  L L L  
F X X X B
B X X X R
F X X X B
  R F R  
```
الحركات: `R2 U R U R' U' R' U' R' U R' U'`

### احتمال 8.3% — 12 STM — `Ua U'`

```
  L L L  
F X X X B
R X X X F
F X X X B
  R B R  
```
الحركات: `R U' R U R U R U' R' U' R2 U'`

### احتمال 8.3% — 23 STM — `Ub U2 Ua`

```
  F R F  
R X X X L
F X X X B
R X X X L
  B L B  
```
الحركات: `R2 U R U R' U' R' U' R' U R' U2 R U' R U R U R U' R' U' R2`

### احتمال 8.3% — 23 STM — `Ua U' Ua`

```
  L F L  
F X X X B
L X X X R
F X X X B
  R B R  
```
الحركات: `R U' R U R U R U' R' U' R2 U' R U' R U R U R U' R' U' R2`

### احتمال 8.3% — 23 STM — `Ub U' Ub`

```
  L R L  
F X X X B
B X X X F
F X X X B
  R L R  
```
الحركات: `R2 U R U R' U' R' U' R' U R' U' R2 U R U R' U' R' U' R' U R'`

### احتمال 6.2% — 0 STM — ``

```
  B B B  
L X X X R
L X X X R
L X X X R
  F F F  
```
الحركات: ``
