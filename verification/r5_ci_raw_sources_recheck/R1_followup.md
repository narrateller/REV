# Q-R1-CI-SEMANTICS-ARBITRATION-01 — unsupported OPEN journal guard

- @R1,P1,REOPENED;parent T-r4-cycle-interfaces-01;blocker R5-CI-B03.
- C b89854ad709bcb5c2991376bed41bf2f73acef82,H ce1ad73aae7a5700203103c14290375cc519662b,
  R1 3aa5ee100f57aa75315d429afef38f8a982b1afc;R5/r5-ci-raw-sources-20261113.
- Старый journal witness/8вариаций исправлены,231/231;new raw exception isolation
  и invalid raw controls проходят. Это не регрессия самого raw FALSE fallback.
- New gap: OPEN record origin.guard=null/bool/int/container/unsupported ID имеет
  coherent F-ID и history_valid=True, но не классифицируется по fixed definitions.
  Scan пропускает запись, journal EVALUATED/TRUE, candidate IN_DOMAIN/TRUE/
  ALLOWED_ASSUMED при всех raw TRUE. Missing guard вместоnull даёт UNKNOWN.
- Independent732records696matches36falseTRUErecords,одинкласс;18orderedinputs,
  6canonicaltypedmaps. Положительный knownFEED control ALLOWED,unknownrecord
  не превращается в blanket FALSE. Inputs/caller readonly,actual moves notrun.
- reproduce_guard_tag.py/minimal_guard_tag_witness.json,independent_results.json,
  review.md содержат результаты и fixed guard membership oracle.
- Применимый критерий R1§3/5: raw TRUE и digest не доказывают отсутствие latch
  при семантически неразрешимой OPEN записи. Legacy equality за пределами
  допустимой схемы не оправдывает успех. Уточнить positive journal admission;
  полный journal repair/W02 не требуется и reviewer-ом не реализуется.
- Седьмой REJECT;история6и material2 сохранена. По§6.1 дальнейшая коррекция
  BLOCKED до записанного решения/плана R1. Norm/helper/44bindings/4variants/calcs/
  CAD/численные параметры не менять. Физика/производство/сроки UNKNOWN/NOT_RUN.

| Вариант | Требования/документальная семантика | Физика/CAD/производство | Риск/неизвестное | Решение |
|---|---|---|---|---|
| A: неизвестный/невалидный guard OPEN записи не может подтверждать отсутствие own fault | Journal positive UNKNOWN,raw FALSE по-прежнему BLOCKED,known unrelated supported guards разрешены | Без product/CAD решений,NOT_RUN | Требуется явно закрепить classification/admission scope,не расширять global domain snapshot требования | Рекомендуемый narrow follow-up и independent RECHECK |
| B: unknown OPEN guard молча считать неприменимым | Даёт TRUE на null/unsupported tag,не доказывает отсутствие latch | Физика NOT_RUN | Требуется принять/описать внешнюю доверенную prevalidation,которая сейчас не реализована этим gate | Не молчаливая приёмка;нужно решение R1 о границе/требовании |
| C: расширить frozen helper/material engine | Отдельная версия/задача,не требуется для safe UNKNOWN admission | Вне текущего scope | Нарушает frozen identity без разрешения | Отдельное решение/review |

Следующий тест: missing/null/unknown/type-alias guard с coherent hashes,
first/middle/last и две own current conditions;valid proof и raw TRUE не дают
recovery на unclassifiable OPEN record;UNKNOWN не blanket FALSE;raw FALSE
сохраняется. Supported unrelated FEED/старые scoped guards остаются положительными.
Не repair/drop record,не подставлять target/domain/revision. Повторить все прежние
regressions и protection/readonly. W02/physicalREADY NO-GO,G1OPEN,architecture/TZ
notapproved;strength/geometry/CAD/rebuild/physicaltrials NOT_RUN.
