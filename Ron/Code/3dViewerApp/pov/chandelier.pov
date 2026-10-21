// chandelier.pov - brass chandelier, lit candles, glass crystals, hazy room.
// Hand-authored for POV-Ray 3.7/3.8.  Render (from the pov/ folder in WSL):
//   povray +Ichandelier.pov +Ochandelier.png +W1200 +H900 +A0.25 +AM2 +R3 +Q11
#version 3.7;

#include "colors.inc"
#include "textures.inc"
#include "metals.inc"
#include "golds.inc"
#include "glass.inc"
#include "woods.inc"

global_settings {
    assumed_gamma 1.0
    max_trace_level 12
    radiosity {
        brightness 1.0
        count 150
        error_bound 0.4
        recursion_limit 2
        nearest_count 8
        gray_threshold 0.0
    }
    photons { count 220000 }      // caustics through the crystals
}

// ---------------------------------------------------------------- camera
// a little below the fitting, looking up; mild focal blur for depth
camera {
    perspective
    location  <0.0, 2.2, -9.2>
    look_at   <0.0, 2.9, 0.0>
    angle 46
    aperture 0.14 focal_point <0.0, 3.2, 0.0> blur_samples 24
}

// ---------------------------------------------------------------- room
#declare WarmPlaster =
    texture { pigment { color rgb <0.22, 0.17, 0.13> }
              finish  { diffuse 0.75 ambient 0.0 } };

// floor: dark polished wood, softly reflective
#declare PolishedFloor =
    material {
        texture { T_Wood7
                  normal  { wood 0.12 scale 0.9 }
                  finish  { diffuse 0.45 ambient 0.0 specular 0.35 roughness 0.015
                            reflection { 0.10, 0.30 fresnel on } }
                  scale 1.6 rotate <4, 20, 0> }
        interior { ior 1.5 }
    };

box { <-18,-0.02,-18>, <18, 7.6, 18>          // the enclosing room (seen from inside)
      hollow
      texture { WarmPlaster }
      interior { ior 1.0 }
}
plane { y, 0 material { PolishedFloor } }

// a faint back wall highlight so the metal has something to reflect
plane { z, 14 texture { pigment { color rgb <0.28,0.22,0.17> } finish { diffuse 0.7 } } }

// ---------------------------------------------------------------- materials
#declare Brass =
    texture { T_Brass_3B
              finish { ambient 0.0 diffuse 0.35 brilliance 2
                       specular 0.6 roughness 0.008 metallic
                       reflection { 0.35, 0.55 metallic fresnel on } } };

#declare WaxCandle =
    texture { pigment { color rgb <0.94, 0.90, 0.80> }
              finish  { ambient 0.06 diffuse 0.8 specular 0.12 roughness 0.1 } };

#declare Crystal =
    material {
        texture { pigment { color rgbf <0.97, 0.98, 1.0, 0.92> }
                  finish  { ambient 0.0 diffuse 0.02
                            specular 0.9 roughness 0.001
                            reflection { 0.08, 0.5 fresnel on } } }
        interior { ior 1.6 dispersion 1.05 dispersion_samples 8 fade_power 1001
                   fade_distance 4 fade_color <0.9,0.93,1.0> }
    };

// ---------------------------------------------------------------- a candle + flame
// built around the origin, candle cup sitting at y=0, pointing +y
#macro CandleFlame(seed_n)
    union {
        // bobeche (drip pan) + cup
        difference { cylinder { <0,-0.02,0>, <0,0.10,0>, 0.34 }
                     cylinder { <0,0.02,0>, <0,0.12,0>, 0.24 } texture { Brass } }
        torus { 0.30, 0.045 translate y*0.10 texture { Brass } }
        cylinder { <0,0.10,0>, <0,0.28,0>, 0.16 texture { Brass } }
        // wax candle
        cylinder { <0,0.28,0>, <0,1.05,0>, 0.135 texture { WaxCandle } }
        // slight melted lip
        torus { 0.135, 0.03 translate y*1.05 texture { WaxCandle } }
        // wick
        cylinder { <0,1.05,0>, <0,1.14,0>, 0.012 pigment { color rgb <0.05,0.04,0.03> } }
        // flame body - emissive, teardrop from two cones + media glow
        union {
            cone { <0,1.10,0>, 0.055, <0,1.26,0>, 0.085 }
            cone { <0,1.26,0>, 0.085, <0,1.62,0>, 0.0 }
            pigment { color rgb <1.0, 0.72, 0.28> }
            finish  { emission 2.6 diffuse 0 ambient 0 }
            hollow
            interior { media { emission <1.1, 0.55, 0.12>*6
                               scattering { 1, <0.5,0.3,0.1> } } }
        }
        // inner blue-white hot core
        sphere { <0,1.20,0>, 0.03
                 pigment { color rgb <0.7,0.8,1.0> } finish { emission 4 } }
        translate <2.28, 0.78, 0>            // sit on the arm tip
    }
    // the light this candle casts - warm, soft, falls off
    light_source {
        <0, 1.25, 0> color rgb <1.0, 0.68, 0.34> * 2.6
        area_light x*0.14, z*0.14, 3, 3 adaptive 1 jitter circular orient
        fade_distance 3.2 fade_power 2
        translate <2.28, 0.78, 0>
    }
#end

// ---------------------------------------------------------------- a swept brass arm
// curves out from the hub (at <0,0,0>) and up to a candle; +x direction
#macro Arm()
    union {
        sphere_sweep {
            cubic_spline
            6,
            <0.00,  0.05, 0>, 0.075
            <0.70, -0.30, 0>, 0.070
            <1.45, -0.28, 0>, 0.065
            <2.05,  0.05, 0>, 0.062
            <2.25,  0.55, 0>, 0.060
            <2.28,  0.78, 0>, 0.058
        }
        // little scrollwork ball mid-arm
        sphere { <1.45,-0.28,0>, 0.12 }
        texture { Brass }
    }
#end

// ---------------------------------------------------------------- the chandelier
#declare HUB = 4.5;        // height of the hub above the floor

union {
    // ---- central turned column ----
    union {
        sphere   { <0,0,0>, 0.42 }                               // bottom finial
        cone     { <0,0.30,0>, 0.38, <0,0.95,0>, 0.18 }
        torus    { 0.30, 0.07 translate y*0.62 }
        cylinder { <0,0.95,0>, <0,1.95,0>, 0.14 }
        torus    { 0.22, 0.06 translate y*1.35 }
        sphere   { <0,1.95,0>, 0.30 }                            // hub ball (arms spring here)
        cone     { <0,2.10,0>, 0.22, <0,2.75,0>, 0.10 }          // upper stem toward chain
        texture { Brass }
        translate y*(HUB-1.95)                                   // sit hub at y=HUB
    }

    // ---- 6 arms + candles around the hub ----
    #declare i = 0;
    #while (i < 6)
        union {
            Arm()
            CandleFlame(i)
            rotate y*(i*60)
            translate y*HUB
        }
        #declare i = i + 1;
    #end

    // ---- lower crystal hoop ----
    torus { 1.15, 0.05 texture { Brass } translate y*(HUB-0.55) }

    // ---- hanging crystal drops around the hoop (briolette bicones) ----
    #declare j = 0;
    #while (j < 12)
        #declare a = j*30;
        union {
            cylinder { <0,0,0>, <0,-0.06,0>, 0.012 texture { Brass } }   // link
            union {                                                       // bicone crystal
                cone { <0,-0.06,0>, 0.0,  <0,-0.20,0>, 0.085 }
                cone { <0,-0.20,0>, 0.085,<0,-0.42,0>, 0.0 }
                material { Crystal }
                photons { target reflection on refraction on }
            }
            translate <1.15, HUB-0.55, 0>
            rotate y*a
        }
        #declare j = j + 1;
    #end

    // ---- a few larger crystals hung under each candle arm ----
    #declare k = 0;
    #while (k < 6)
        union {
            cylinder { <0,0,0>, <0,-0.08,0>, 0.012 texture { Brass } }
            union {
                cone { <0,-0.08,0>, 0.0,  <0,-0.26,0>, 0.11 }
                cone { <0,-0.26,0>, 0.11, <0,-0.55,0>, 0.0 }
                material { Crystal }
                photons { target reflection on refraction on }
            }
            translate <1.55, HUB-0.05, 0>
            rotate y*(k*60 + 30)
        }
        #declare k = k + 1;
    #end

    // ---- chain up to the ceiling + canopy ----
    #declare c = 0;
    #while (c < 7)
        torus { 0.11, 0.028 texture { Brass }
                rotate x*90 rotate y*(c*55)
                translate y*(HUB + 2.75 + c*0.19) }
        #declare c = c + 1;
    #end
    cone { <0,7.35,0>, 0.05, <0,7.58,0>, 0.42 texture { Brass } }   // ceiling canopy
}

// ---------------------------------------------------------------- room ambience
// one very dim cool fill from a "window" off-left so shadows aren't pure black
light_source {
    <-14, 7, -10> color rgb <0.16, 0.19, 0.26>
    area_light x*3, y*3, 3, 3 adaptive 1 jitter
    fade_distance 20 fade_power 1
}

// ---------------------------------------------------------------- volumetric haze
// a big hollow box of faint scattering media so the candle light carries through
// the air (soft glow / smoke).  Kept subtle so it reads as atmosphere, not fog.
box { <-17, 0.05, -17>, <17, 7.5, 17>
      hollow
      pigment { rgbt 1 }
      interior { media {
          scattering { 1, <0.5, 0.42, 0.33> * 0.018 extinction 0.4 }
          samples 12, 40
          method 3
      } }
}
