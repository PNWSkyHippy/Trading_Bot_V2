# Camera Director

Open **Camera Director…** beside the render buttons (also on the Edit menu).
This window plans camera movement without rendering expensive frames.

## Start with an existing POV scene

1. On **Save/load**, choose your existing `.pov` file and enable using it as the background scene.
2. Click **Start path at scene's camera / aim**. For a camera written with literal XYZ numbers, this moves the path to that camera and puts the reference object at its look-at point. Expressions such as `<X, Height, -10>` cannot be imported automatically; enter those coordinates yourself.
3. On **Object/lights**, set the reference object's position and size to roughly match your subject. Set **ground Y** to your scene's floor height. This is a preview reference, not a new rendered floor.
4. Edit moves, use **Apply**, then scrub or play the wireframe preview.
5. On **Save/load**, click **Use complete scene with POV-Ray**. Back in the main window, use the POV sequence/strip render. The POV still render uses the first camera pose.

The original POV file stays intact. Rendering creates a temporary scene with the planned camera and added lights, retaining the source's geometry, includes and existing lights. Added lights are additive: an already bright scene may need fewer or dimmer new lights. The reference object is only inserted into an existing scene if you enable that option.

The replacement camera is a standard perspective camera. Special settings in the original camera block, such as depth of field, roll or a different camera type, are not retained.

## Coordinates and movement

- The editor uses **Y up**. Top view shows X/Z; front shows X/Y; side shows Z/Y. Dragging changes those two visible coordinates. The XYZ text fields let you change the third coordinate.
- Pick the marker you want to place, then click the map or drag its handle. Use the mouse wheel to zoom and **Fit** to bring the path back into view.
- A **Line** travels from Start A to End B. An **Arc** travels from Start A to End C and passes through B halfway along the move. This is a smooth quadratic curve, not necessarily a circular arc.
- Camera position and camera aim are separate. Start/end aim points let the camera pan as it travels. **Aim this move at object** keeps both ends aimed at the reference object's position.
- Start/end FOV controls zoom. These numbers are vertical field-of-view angles in degrees; smaller numbers zoom in.
- Moves join together. Editing a move's endpoint also updates its neighbor so the camera does not jump between moves.
- **Steps** means intervals: a single 48-step move produces 49 frames, including both ends. Multiple moves share their joining frame. The director's steps determine the render count, overriding the main Movie Frames setting while that path is active.
- FPS controls preview timing. It does not add frames.
- **POV camera roll (degrees, all moves)** on Object/lights tilts the camera around its viewing direction without changing its path or aim. For a sideways image, try 90 or -90, click Apply and inspect the preview. This one setting covers the entire sequence and is saved with the project/preset. Click Use complete scene with POV-Ray again to send the change to the renderer. Roll is supported by the preview and POV renderer, not the homemade/book renderer.

Red path sections and the warning identify sampled camera positions below your reference ground Y. This helps catch underground paths, but is not collision detection. The wireframe shows the reference object, lights, axes and grid; it does not parse and display all objects or terrain in an arbitrary POV scene. Use a small test render to check the actual scene before a long sequence.

## Save and export

**Save named preset** stores editable data in the marked `camera_director_shots` section at the end of `rayincludes.py`. Your original hand-written scenes remain outside that section. A `.py.director.bak` backup is made before saving. Loading a preset restores the path, reference object, lights and saved background-scene choice.

**Save project JSON** creates a separate editable project; **Open project JSON** restores it.

**Export POV scene + frame list** writes four companion files:

- `.pov`: scene with an animated camera and your lights.
- `.ini`: POV-Ray settings for rendering the exported animation's complete frame range.
- `.frames.json`: camera frame list for the existing renderer interface.
- `.project.json`: editable director settings.

Run the exported `.ini` with POV-Ray to render that animation independently. For an existing POV scene, export beside the original so relative include paths continue to work. The editor refuses to overwrite the original background scene.

For the homemade/book renderer, choose **Use path with book renderer**. It uses the current book's geometry and the new camera path; its existing interface supports only the first two lights as white lights with brightness limited to 0–1. POV-Ray uses all director lights, with their colors and brightness.

Choose **Edit → Use original rayincludes camera path** in the main window to return to the old path generator.

## Where to change the code

- `camera_path.py`: plain dictionaries, curve calculations, validation, POV text generation and preset saving. No Tk widgets here.
- `camera_path_editor.py`: editor controls, map drawing, wireframe preview and playback. It passes a copied shot to the main window when you click Use.
- `tkray_tracer.py`: opens the editor and connects its output to the existing render queues and progress reporting.
- `test_camera_path.py`: focused checks for paths, source preservation, exports and the Tk/renderer connection.

The important distinction is between a **shot** (editable moves and lights) and **frames** (sampled camera poses ready to render). Each render takes a snapshot so subsequent editing does not change frames already queued.
