# Superficies RobotSkin para LeKiwi

Tres recubrimientos de 4 mm: `top.stl` (Z=57–61), `floor.stl` (Z=0–4) y
`ceiling.stl` (Z=46–50, puertos hacia abajo), en milímetros del chasis.

## Fuente de las posiciones

Los soportes, motores, cubos, ruedas y separadores usan las ocurrencias STEP
de `cad/assembly/LeKiwi.FCStd`, identificadas por `ReferenceObject` en el grupo
`LeKiwiReferenceParts`. Son la referencia dimensional física del repositorio.
Se comprueba que los dos agujeros de cada soporte coinciden con agujeros reales
de la placa inferior. El brazo SO-101 y los accesorios añadidos conservan sus
transformaciones actuales.

La primera versión de estas pieles usó las posiciones del URDF heredado.
Ese modelo desplazaba cada soporte aproximadamente 10 mm respecto al STEP;
sus agujeros no coincidían con los del chasis, y dos cubos de rueda invadían
la piel. `wheel_placement_audit.json` registra los desplazamientos y los centros
de tornillos físicos. La corrección de las pieles no modifica automáticamente
las posiciones del URDF de producción.

Los recortes siguen las envolventes convexas orientadas de las piezas reales
que alcanzan la altura de cada piel, con 1 mm de holgura. Se verifican los doce
componentes de las tres unidades de rueda, además de los seis separadores.
La holgura se ajusta con `--clearance` (0.5–3 mm); el borde exterior queda
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
- `full_build.png`: chasis físico completo con SO-101 y accesorios actuales.
- `wheel_assemblies.png`: planta con radios y planos de rueda, y las tres unidades.
- `floor_wheel_fit.png`: piel corregida con motores, soportes, cubos y ruedas.
- `checks.json`, `wheel_placement_audit.json`, `wheel_orientation_checks.json`:
  geometría, fijaciones, comparación de posiciones y orientación de las ruedas.

Las verificaciones exigen mallas cerradas y conectadas, grosor de 4 mm, paso
central libre en todos los puertos y caras dentro de las envolventes comprobadas
(tolerancia STL de 0.002 mm). Las imágenes muestran geometría CAD real, no un
concepto ilustrativo. Los componentes que se remontarán se muestran en sus
posiciones de referencia en la vista del robot completo.

La altura interior libre queda en 42 mm. Las piezas caben aproximadamente en
215 × 212 mm. Falta la prueba física de ajuste, incluida la tornillería real
del brazo, y no se certifica el barrido completo de sus seis ejes.
