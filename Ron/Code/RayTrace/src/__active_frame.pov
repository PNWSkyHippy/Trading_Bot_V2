
camera {
    perspective
    location <-2, 3, 0.0>
    look_at  <0, 3, 0>
    angle 55.625
}

// Key Light (Warm, Primary)
light_source { <6.0, 8.0, -6.0>, color rgb <1.0, 0.55, 0.48> * 1.2 }
// Fill Light (Cool, Soft)
light_source { <-6.0, 4.0, -4.0>, color rgb <0.7, 0.8, 1.0> * 0.5 shadowless }
// Rim Light (Backlight)
light_source { <0.0, 6.0, 8.0>, color rgb <1.0, 1.0, 1.0> * 0.8 }


// Cylinder #8
cylinder {
    <0.0, 0.0, 0.0>, <0.0, 2.5, 0.0>, 0.8
    translate <7.50, 0.0, 0.0>
    pigment { color rgb <0.3, 0.8, 0.4> }
    finish { ambient 0.1 diffuse 0.8 specular 0.3 }
}
plane {
    y, 0
    pigment { checker color rgb <0.776, 0.396, 0.169> color rgb <0.75, 0.75, 0.8> scale 1.5 }
    finish { ambient 0.1 diffuse 0.8 reflection 0.1 }
}


// Cone #9
cone {
    <0.0, 0.0, 0.0>, 1.20, <0.0, 2.5, 0.0>, 0.0
    translate <7.60, 2.80, 0.20>
    texture {
    pigment { color rgb <1.0, 0.84, 0.0> }
    finish { ambient 0.1 diffuse 0.5 reflection 0.75 metallic 0.8 specular 0.85 roughness 0.02 }
    }
}



// Torus #10
torus {
    1.50, 0.4
    rotate <0, 0, 0>
    translate <7.70, 2.50, 0.50>
    texture {
    pigment { color rgbf <0.2, 0.85, 0.4, 0.8> }
    finish { ambient 0.08 diffuse 0.2 reflection 0.25 specular 0.9 roughness 0.01 }
    }
    interior { ior 1.58 }
}





























































































































