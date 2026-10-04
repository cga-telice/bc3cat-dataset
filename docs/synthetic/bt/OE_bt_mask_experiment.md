# Miniexperimento de enmascarado para la BT (OE)

100 consultas de STACKED-P, pivote EN, condición `stacked_bt`, valores de eje y fragmentos L2 enmascarados. Criterio: más aceptación; a igualdad, menos máscaras perdidas.

| Estrategia | Máscara perdida | Valores de orden cambiado | No-ops | Aceptadas | Rechazos por puerta |
|---|---:|---:|---:|---:|---|
| `sentinel` | 82 | 0 | 0 | 16 | {'BT': 82, 'G1': 2} |
| `xml` | 7 | 0 | 0 | 93 | {'BT': 7} |

**Elegida: `xml`.**

## Ejemplos de rechazo (texto enmascarado tras la BT)

- `sentinel`:
  - BT `OEA050dccb_syn_8fe3dc99ae79` mask_lost: Canal de hormigón armado de [[Q1] [[Q2]] resistencia a la compresión, tipo estándar [[V1]] con tapa incluida. Instalación total, incluyendo preparación del suelo, compactación, aplanamiento del suelo, capa de arena de río de [[Q3]], sellado de tapas y conexiones con mortero, y llenado compactado. Tr
  - BT `OEA080kdcc_syn_2264f5066bd7` mask_lost: Instalación y configuración de la tapa para canalización de hormigón tipo [[V1]], que incluye la colocación y remoción de terrenos adicionales. Operaciones: [[V2] Área de trabajo: [[V3]] Circunstancias de aplicación: [[V4]]
  - BT `OEB020ababb_syn_8de054eb412b` mask_lost: Se realizará la canalización enterrada de [[V1] [[[S1]] [[[Q1]] conductos de diámetro nominal [[V2]]. Incluye [[V3]] el llenado y compactación del recinto, la provisión y colocación de tuberías y hormigón de tipo [[Q2]] sin vibración, la verificación de los conductos, el transporte y la retirada al 
  - BT `OEB020dcfbb_syn_3e0fba20261e` mask_lost: Por medio de [[V1]] [[[S1]] tubos de [[Q1]] y diámetro [[[V2]], se llevará a cabo una canalización enterrada, que comprenderá [[V3]] el llenado y compactación de la zanja, la entrega y el montaje de tuberías y hormigón no vibratorio [[Q2], la inspección de los conductos, el transporte y la deposició
  - BT `OEB020ddeca_syn_0492bea666b9` mask_lost: La instalación de una conducción enterrada se llevará a cabo utilizando [[V1] [[[S1]] [[[Q1]]] [[[V2]] mm de diámetro, que incluye [[V3]] el llenado y compactación del pozo, el aprovisionamiento y la colocación de tubos y hormigón de clase [[Q2] no vibrados, la evaluación de los conductos, el despla
- `xml`:
  - BT `OEB020adadb_syn_1fb4f6d42b74` mask_lost: Instalación subterránea de tubos <x1/> de <x2/> de <x3/> con un diámetro de <x4/> mm, llevando a cabo <x5/> el llenado y compactación de la excavación, el suministro y montaje de tubos y encofrados no vibratorios, la evaluación de los conductos, la transferencia y la eliminación de los artículos al 
  - BT `OEB020ddeca_syn_0492bea666b9` mask_lost: La instalación de una conducción enterrada se llevará a cabo utilizando tubos <x1/> de <x2/>x3/> con un diámetro de <x4/>mm, que incluye <x5/> el llenado y compactación del pozo, el aprovisionamiento y la colocación de tubos y hormigón no vibrados, la evaluación de los conductos, el desplazamiento y
  - BT `OEB030hacac_syn_a428956d6620` mask_lost: Instalación de conducción integrada de <x1/> conductos de polietileno sin halógenos de <x2/> con diámetro nominal <x3/>, incluyendo zanja y relleno, y compactación, suministro y colocación de conductos no vibratorios y hormigón, ensayos de conductos, transporte y eliminación de productos al lugar de
  - BT `OEB040ifcbc_syn_73b70454d46a` mask_lost: Configuración de la conducción subterránea con conductos de polietileno <x1/> que no contengan halógenos de <x2/> y diámetro <x3/>, incluido el llenado y compactación del corte, suministro y montaje de tubos y hormigón tipo <x5/> que no vibran, verificación de conductos, transferencia y eliminación 
  - BT `OEB040jcbab_syn_52690ff9f67c` mask_lost: Instalación de conducción enterrada con conductos de polietileno <x1/> sin halógenos de diámetro <x2/> mm <x3/>, incluido el llenado y compactación <x4/> de la zanja. Los conductos y el tipo de hormigón < x5/> se suministrarán y montarán sin vibración, los conductos se someterán a ensayo, transporta
