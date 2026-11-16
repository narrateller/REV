# Условная арифметика — автоматически из исходных bindings

Новые ID относятся только к analysis/params/registry.yaml. Активный реестр неизменён.

| Расчётный ID (revision 1) | Значение SI | Единица | Выражение / область |
|---|---:|---|---|
| `R3F_A_ROD_AREA` | 0.0188511676431 | m2 | pi*d^2/4 |
| `R3F_A_ROD_WORK_STRESS` | -81290319.9959 | Pa | -F_work/(pi*d^2/4) |
| `R3F_A_ROD_RETURN_STRESS` | 636565.343178 | Pa | F_return/(pi*d^2/4) |
| `R3F_A_PUNCH_MEAN_WORK_PRESSURE` | 170268605.556 | Pa | F_work/(width*height) |
| `R3F_A_IDEAL_WORK_N` | -1532417.45 | N | -F_work; compression, ideal serial chain only |
| `R3F_A_IDEAL_RETURN_N` | 12000 | N | F_return; tension, captured ideal serial chain only |
| `R3F_A_WORK_MZ_PER_E` | -1532417.45 | N | -F_work; Mz/e_y, cylinder applied couple |
| `R3F_A_RETURN_MZ_PER_E` | 12000 | N | F_return; Mz/e_y, cylinder applied couple |
| `R3F_A_WORK_R0_PER_E_OVER_A` | -1532417.45 | N | -F_work; ideal guide couple reaction |
| `R3F_A_WORK_R1_PER_E_OVER_A` | 1532417.45 | N | F_work; ideal guide couple reaction |
| `R3F_A_RETURN_R0_PER_E_OVER_A` | 12000 | N | F_return; ideal guide couple reaction |
| `R3F_A_RETURN_R1_PER_E_OVER_A` | -12000 | N | -F_return; ideal guide couple reaction |
| `R3F_A_EULER_BOUNDARY_COEFF` | 155266.349868 | N | F_work/pi^2; EI/L_eff^2 at ideal eigenvalue equality, not allowable |
| `R3F_B_ROD_AREA` | 0.0184833202316 | m2 | pi*d^2/4 |
| `R3F_B_ROD_WORK_STRESS` | -81285041.3872 | Pa | -F_work/(pi*d^2/4) |
| `R3F_B_ROD_RETURN_STRESS` | 649234.003936 | Pa | F_return/(pi*d^2/4) |
| `R3F_B_PUNCH_MEAN_WORK_PRESSURE` | 166935272.222 | Pa | F_work/(width*height) |
| `R3F_B_IDEAL_WORK_N` | -1502417.45 | N | -F_work; compression, ideal serial chain only |
| `R3F_B_IDEAL_RETURN_N` | 12000 | N | F_return; tension, captured ideal serial chain only |
| `R3F_B_WORK_MZ_PER_E` | -1502417.45 | N | -F_work; Mz/e_y, cylinder applied couple |
| `R3F_B_RETURN_MZ_PER_E` | 12000 | N | F_return; Mz/e_y, cylinder applied couple |
| `R3F_B_WORK_R0_PER_E_OVER_A` | -1502417.45 | N | -F_work; ideal guide couple reaction |
| `R3F_B_WORK_R1_PER_E_OVER_A` | 1502417.45 | N | F_work; ideal guide couple reaction |
| `R3F_B_RETURN_R0_PER_E_OVER_A` | 12000 | N | F_return; ideal guide couple reaction |
| `R3F_B_RETURN_R1_PER_E_OVER_A` | -12000 | N | -F_return; ideal guide couple reaction |
| `R3F_B_EULER_BOUNDARY_COEFF` | 152226.714359 | N | F_work/pi^2; EI/L_eff^2 at ideal eigenvalue equality, not allowable |
