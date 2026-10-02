// ==============================================================================
// 500-Yard Textured Tunnel Scene (POV-Ray Format)
// ==============================================================================

#version 3.7;

global_settings {
    assumed_gamma 1.0
}

#include "colors.inc"

// ------------------------------------------------------------------------------
// Camera: Dead center (0, 0, 0) looking straight forward (+Z)
// ------------------------------------------------------------------------------
camera {
  location <0,0,20.8333333>
  right x*image_width/image_height
  sky <0,1,0>
  angle degrees(2*atan(tan(radians(45.0/2))*image_width/image_height))
  look_at <0,0,120.833333>
}

// ------------------------------------------------------------------------------
// Tunnel Geometry & Textures
// ------------------------------------------------------------------------------

// SECTION 1 (0 to 100 yards)
cylinder {
    <0, 0, 0>, <0, 100, 0>, 3.5
    open
    hollow
    texture {
        pigment {
            image_map {
                jpeg "section1.jpg"
                map_type 2
                interpolate 2
            }
            scale <-1, 100, 1>
            rotate <0, 90, 0>
        }
        finish { ambient 0.15 diffuse 0.85 specular 0.2 roughness 0.05 }
    }
    rotate <90, 0, 0>
    translate <0, 0, 0>
}

// SECTION 2 (100 to 200 yards)
cylinder {
    <0, 0, 0>, <0, 100, 0>, 3.5
    open
    hollow
    texture {
        pigment {
            image_map {
                jpeg "section2.jpg"
                map_type 2
                interpolate 2
            }
            scale <-1, 100, 1>
            rotate <0, 90, 0>
        }
        finish { ambient 0.15 diffuse 0.85 specular 0.2 roughness 0.05 }
    }
    rotate <90, 0, 0>
    translate <0, 0, 100>
}

// SECTION 3 (200 to 300 yards)
cylinder {
    <0, 0, 0>, <0, 100, 0>, 3.5
    open
    hollow
    texture {
        pigment {
            image_map {
                jpeg "section3.jpg"
                map_type 2
                interpolate 2
            }
            scale <-1, 100, 1>
            rotate <0, 90, 0>
        }
        finish { ambient 0.15 diffuse 0.85 specular 0.2 roughness 0.05 }
    }
    rotate <90, 0, 0>
    translate <0, 0, 200>
}

// SECTION 4 (300 to 400 yards)
cylinder {
    <0, 0, 0>, <0, 100, 0>, 3.5
    open
    hollow
    texture {
        pigment {
            image_map {
                jpeg "section4.jpg"
                map_type 2
                interpolate 2
            }
            scale <-1, 100, 1>
            rotate <0, 90, 0>
        }
        finish { ambient 0.15 diffuse 0.85 specular 0.2 roughness 0.05 }
    }
    rotate <90, 0, 0>
    translate <0, 0, 300>
}

// SECTION 5 (400 to 500 yards)
cylinder {
    <0, 0, 0>, <0, 100, 0>, 3.5
    open
    hollow
    texture {
        pigment {
            image_map {
                jpeg "section5.jpg"
                map_type 2
                interpolate 2
            }
            scale <-1, 100, 1>
            rotate <0, 90, 0>
        }
        finish { ambient 0.15 diffuse 0.85 specular 0.2 roughness 0.05 }
    }
    rotate <90, 0, 0>
    translate <0, 0, 400>
}

// Far End Cap (Z = 500 yards)
disc {
    <0, 0, 500>, <0, 0, 1>, 3.5
    pigment { color rgb <0.02, 0.02, 0.02> }
    finish { ambient 0.1 diffuse 0.2 }
}

// ------------------------------------------------------------------------------
// Overhead Lighting System (Every 15 yards from 0 to 500 yards)
// ------------------------------------------------------------------------------
#for (ZPos, 7.5, 492.5, 15.0)
    light_source {
        <0.0, 3.25, ZPos>,
        color rgb <1.0, 0.98, 0.94> * 1.15
        fade_distance 15.0
        fade_power 2
        shadowless
    }

    cylinder {
        <0, 3.25, ZPos - 0.6>, <0, 3.25, ZPos + 0.6>, 0.08
        pigment { color rgb <1.0, 0.98, 0.94> }
        finish { ambient 1.5 diffuse 0.0 }
        no_shadow
    }
#end
// Camera Director additions (original lights retained)

light_source { <-4,8,-6> color rgb <1.5,1.5,1.5> }
