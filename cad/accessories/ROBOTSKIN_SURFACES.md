# Superficies RobotSkin para LeKiwi

Tres recubrimientos desmontables sobre las placas existentes, en milímetros:

| STL | Cara | Z instalada | Puertos |
| --- | --- | --- | --- |
| `top.stl` | Superior exterior | 57–61 | 182 |
| `floor.stl` | Piso interior | 0–4 | 235 |
| `ceiling.stl` | Techo interior, puertos hacia abajo | 46–50 | 300 |

El generador toma el perímetro de las placas editables de FreeCAD, las posiciones
de los tres soportes de motor y los seis separadores metálicos del ensamblaje,
y la base SO-101 instalada mediante la misma transformación del exportador.
La superior reserva la envolvente rectangular de la base y abre el recorte
hacia el frente (+Y). El piso reserva las envolventes de los soportes. Las tres
caras dejan acceso a los separadores y sus tornillos: radio mínimo de 5 mm.
Los demás componentes se omiten, según el montaje propuesto sobre RobotSkin.

La separación respecto a esas envolventes es de 1 mm, ajustable mediante
`--clearance` (0.5–3 mm). El perímetro queda 0.5 mm dentro del chasis.
El grosor de 4 mm, los puertos octagonales, sus alojamientos para insertos y
la retícula de 10 mm reutilizan directamente `port_cut()` del submódulo
RobotSkin fijado por LeKiwi. Se conservan `RM_PORT_FIT`, `RM_PEG_FIT` y
`RM_INSERT_BORE`; no se redefine la interfaz. Sólo se colocan puertos completos
con margen de pared en los recortes y alrededor de los tornillos.

## Generar y revisar

Desde la raíz de LeKiwi, con FreeCAD Flatpak, OpenSCAD y Python con trimesh y Shapely 2:

```sh
./scripts/build_robotskin_surfaces.sh
# Opcional: imagen de las mallas reales, requiere VTK.
python3 scripts/render_robotskin_surfaces.py
```

Los resultados reproducibles quedan en `cad/generated/robotskin/`:

- `top.stl`, `floor.stl`, `ceiling.stl`: orientación de impresión, base en Z=0,
  puertos arriba. El techo está reflejado en Y para quedar alineado al voltearlo.
- `LeKiwi_RobotSkin.FCStd`: ensamblaje de revisión con las tres mallas instaladas,
  placas originales, soportes, separadores y brazo. La receta editable está en
  `robotskin_surfaces.scad` y `scripts/build_robotskin_surfaces.py`.
- `preview.png`: caras expuestas y despiece de las tres láminas.
- `checks.json`: coordenadas, puertos y volúmenes verificados.

Cada ejecución comprueba que los tornillos coinciden con agujeros reales de
las placas, que las envolventes no intersectan soportes/separadores/placas,
y que las mallas finales son cerradas, orientadas y conectadas, con grosor de
4 mm y vértices y caras dentro de esas envolventes (tolerancia STL de 0.002 mm).
Los recortes del brazo incluyen
su base fija y cualquier visual que alcance la altura de la lámina en postura
neutra. No se ha certificado el barrido completo de los seis ejes del brazo.

## Montaje

Las tres láminas usan cuatro pasos M3 de 3.4 mm en las coordenadas CAD
(-60,-60), (60,-60), (-80,-20), (80,-20). Los dos recubrimientos de la placa
superior comparten esos tornillos: apilar superior + placa original + techo
da 15 mm; el piso con su placa suma 11 mm. Elegir la longitud de tornillo
añadiendo las arandelas, tuerca y su enganche real. Estos pasos son de fijación
al chasis; los puertos RobotSkin conservan sus insertos ciegos independientes.

Mantener el brazo y los separadores asentados directamente en sus placas
originales; los recubrimientos no quedan bajo sus apoyos. El techo puede
requerir retirar la placa superior para instalarse. Revisar también el espacio
de las tuercas reales del brazo antes del montaje: no están detalladas como
piezas independientes en este CAD. La altura interior libre pasa de 50 a 42 mm.
Las láminas miden aproximadamente 215 × 212 mm; comprobar el área de impresión
y calibrar un puerto antes de imprimirlas completas. La comprobación digital
no sustituye la prueba de ajuste físico ni establece capacidad de carga.

El ensamblaje de revisión es independiente: no modifica el CAD principal,
el URDF ni las piezas que siguen en desarrollo.
