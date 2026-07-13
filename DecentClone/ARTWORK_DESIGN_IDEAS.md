Those three would make excellent polished tunnel themes:
Black-gloss sci-fi: seamless dark metallic panels, subtle seams, emissive strips, and controlled reflections.
Underwater glass tube: glass should come from the tunnel material/shader; the texture supplies edge framing, seals, condensation, and scratches. Ocean scenery belongs outside the tunnel.
Glass tube in clouds: the same glass material, but with a bright atmospheric sky environment, cloud layers, sunlight, and occasional structural ribs.
The important distinction is that we shouldn’t wrap ocean or sky artwork around the inside of the tunnel—that caused the squashed appearance. We need seamless tunnel-surface textures plus separate exterior environments. When you’re ready, I can generate a coordinated texture set designed specifically for cylindrical wrapping, including color, normal, roughness, metallic, emissive, and opacity maps where needed.


8:48 AM






yreash designed for the size and flat or round mapping going on one tile for an entir unne section would be ideal





8:49 AM






Worked for 59s



Exactly. I checked the renderer: the UVs already map cleanly with U around the tunnel and V along its length, but the shader currently repeats every texture 6 times around × 15 times along. That would ruin a purpose-built full-section texture.
The correct setup is:
New tunnel textures: 2048×1024, cylindrical/equirectangular layout.
One horizontal wrap around the tunnel and one vertical span per section.
Perfectly seamless left/right edges.
Optional legacy tiling retained per texture in the manifest.
Separate spherical mapping variants for chambers.
Black-gloss, underwater-glass, and cloud-glass each authored for this exact projection.
A small renderer change should add per-texture tileU and tileV, with the new themes set to 1 × 1 and existing rock/metal textures remaining 6 × 15. Then the art will fit one entire section instead of looking like a flattened sky photograph.


8:50 AM






scaled due to tunnel diameter but that should be okay





8:50 AM






Yes. Diameter will stretch the texture around a wider circumference, but that should look natural for clouds, water, reflections, and broad sci-fi panels.
For heavily structured textures, we can compensate by selecting mapping density from the tunnel diameter—or use repeating structural ribs while keeping the scenic layer at one full wrap. That avoids enormous panels in unusually wide chambers while preserving the intended panoramic appearance.


8:51 AM






then im thinking custom textures to use at branchs to another tunnel now they are hard to spot sometimes as the blend in if it depicts a framed archway anywhere a new tunnel breaks off  it would help





8:52 AM






That would help enormously, but it should be attached procedurally to the actual branch opening rather than baked into the main wall texture. Branches can appear at any rotation, diameter, and position, so a baked arch could miss the opening.
I’d render a junction collar automatically wherever tunnels connect:
Circular or hexagonal frame surrounding the branch mouth.
Emissive edge lighting visible against every wall texture.
Slightly raised rim so it remains obvious at shallow viewing angles.
Optional directional chevrons pointing into the branch.
Configurable frame texture/color per junction.
Full 360° design—no implied “top,” since the tunnels are zero-gravity.
Stronger glow when the branch is near the player, with restrained distance falloff.
For glass themes, it could resem
