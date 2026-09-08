# Superficies RobotSkin para LeKiwi

Tres recubrimientos de 4 mm: `top.stl` (Z=57–61), `floor.stl` (Z=0–4) y
`ceiling.stl` (Z=46–50, puertos hacia abajo), en milímetros del chasis.

## Fuente de las posiciones

El soporte autoritativo es `3DPrintMeshes/drive_motor_mount_v2.stl`, indicado
por el usuario. Su reconstrucción paramétrica mide **47.5 × 34.8 × 45.5 mm**
(ancho tangencial × profundidad radial × altura instalada), no 50 × 37 mm.
Los cuatro ejes de fijación de cada soporte coinciden con agujeros del chasis;
el borde exterior queda 1.25 mm dentro del segmento plano. Las tres unidades
se orientan a 120°, con los ejes de rueda radiales y los planos tangenciales.

Soportes, motores, cubos, ruedas y seis separadores se obtienen de los `CadParts`
activos y las posiciones articulares de `cad/assembly/LeKiwi.FCStd`.
Los separadores están en (±100, 0) y (±60, ±80) mm, en los tornillos señalados.
El brazo SO-101 y los accesorios conservan sus transformaciones actuales.

Los recortes reservan **4 mm por cada lado** de las envolventes convexas XY
de las unidades de rueda que alcanzan la altura de cada piel. La huella nominal
del soporte con ese margen mide 55.5 × 42.8 mm; otros componentes pueden
ampliar el recorte. `--motor-clearance` ajusta el margen independientemente
de las otras holguras. `motor_bases` conserva las huellas y recortes verificados.
El techo también deja espacio para los soportes de 45.5 mm de altura.
Los seis separadores se comprueban en las tres pieles.
Las dos ventanas de cables se derivan del perfil CAD superior: 60 × 20 mm
centrada en (0, 0) y 20 × 30 mm en (0, 50), ambas con esquinas R4.
Son aproximaciones de la fotografía usando la retícula de 20 mm, no medidas
con calibre. El techo conserva ambas; la piel superior también las despeja,
aunque pueden unirse al recorte del brazo. El piso no cambia.
La holgura general se ajusta con `--clearance` (0.5–3 mm); el borde exterior queda
0.5 mm dentro del perímetro de la placa. Los componentes electrónicos no
recortan la piel: se remontarán encima, según el montaje solicitado.

## Fijación usando los puertos normales

No hay agujeros adicionales de montaje. Todos los puertos usan `port_cut()`
y el paso central de `through_plate()` de la biblioteca RobotSkin existente.
La retícula de 10 mm parte del origen del chasis, por lo que coincide con su
retícula de tornillos de 20 mm. `chassis_ports` en `checks.json` enumera los
puertos que coinciden con agujeros físicos utilizables de cada placa.

Fijar las pieles por esos mismos puertos, con tornillos M3 y los insertos de
RobotSkin. Usar un único inserto por unión: no enroscar un tornillo a través
de dos insertos enfrentados. La placa superior con sus dos pieles suma 15 mm;
la inferior con su piel suma 11 mm. Elegir la longitud según cabeza, arandelas
y enganche del inserto. Se conservan los ajustes de impresión `RM_PORT_FIT`,
`RM_PEG_FIT` y `RM_INSERT_BORE` de la biblioteca fijada por LeKiwi.

## Regenerar e inspeccionar

Requiere FreeCAD Flatpak, OpenSCAD y Python con trimesh, Shapely 2 y rtree;
las imágenes usan VTK. Desde la raíz del repositorio:

```sh
./scripts/build_robotskin_surfaces.sh
python3 scripts/render_robotskin_surfaces.py
python3 scripts/render_robotskin_assembly.py
```

Resultados en `cad/generated/robotskin/`:

- `top.stl`, `floor.stl`, `ceiling.stl`: impresión con puertos arriba y base Z=0.
  El techo se refleja en Y para recuperar las coordenadas CAD al voltearlo.
- `LeKiwi_RobotSkin.FCStd`: ensamblaje de revisión con las pieles instaladas.
- `preview.png`: las tres pieles y despiece.
- `full_build.png`, `wheel_assemblies.png`: CAD corregido y unidades de rueda.
- `floor_base_fit.png`: STL del piso y huellas v2 con 4 mm por lado.
- `floor_wheel_fit.png`: piso instalado y conjuntos completos de rueda.
- `checks.json`, `wheel_orientation_checks.json`: geometría, fijaciones y ejes.

Las verificaciones exigen mallas cerradas y conectadas, grosor de 4 mm, paso
central libre en todos los puertos y caras dentro de las envolventes comprobadas
(tolerancia STL de 0.002 mm). Los componentes que se remontarán se muestran en sus
posiciones de referencia en la vista del robot completo.

La altura interior libre queda en 42 mm. Las piezas caben aproximadamente en
215 × 212 mm. Falta la prueba física de ajuste, incluida la tornillería real
del brazo, y no se certifica el barrido completo de sus seis ejes.

La referencia de servo tiene pequeñas intersecciones de esquina con el soporte
v2 (menos de 1 mm³ por unidad, también presentes contra el STL original).
Esto no es una colisión con RobotSkin ni una certificación de ajuste físico
servo/soporte. No se ha deformado el soporte oficial para ocultarlas.

Verificación del 2026-09-08: `verify_robot.sh`, `compare_reauthored_assets.sh --strict`,
`verify_robotskin_surfaces.py`, `correct_chassis_rods.py` e `install_wheel_mount_v2.py`
aprobados. Puertos completos: superior 179, piso 222, techo 222. Piso y techo
conservan seis agujeros independientes para separadores; dos claros superiores
se abren al recorte del brazo. Desviación máxima eje/radio en las tres ruedas:
0.172°. Las imágenes proceden de geometría CAD/STL, no de una ilustración generada.
