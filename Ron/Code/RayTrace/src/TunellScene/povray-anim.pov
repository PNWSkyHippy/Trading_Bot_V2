// ==============================================================================
// POV-Ray 3.7+ Scene: 500-Yard Continuous 5-Section Textured Tunnel
// ==============================================================================

#version 3.7;

global_settings {
    assumed_gamma 1.0
    ambient_light rgb <0.15, 0.15, 0.15>
}

#include "colors.inc"

// ==============================================================================
// USER CONFIGURATION PARAMETERS
// ==============================================================================

// Dimensions (1 unit = 1 yard)
#declare SectionLength   = 100.0;       // Length of each section (yards)
#declare NumSections     = 5;           // 5 sections total = 500 yards
#declare TotalLength     = NumSections * SectionLength; // 500.0 yards
#declare TunnelRadius    = 3.5;         // Tunnel radius (~10.5 ft / 21 ft diameter)

// Texture Mapping Controls
#declare RepeatLengthwise = 1.0;        // Times image tiles lengthwise per section
#declare SeamAngle        = 90.0;       // Rotation around axis to position seam at floor/ceiling

// Image files for each of the 5 sections (JPG, PNG, or TGA)
#declare ImageFiles = array[5] {
    "section1.jpg",
    "section2.jpg",
    "section3.jpg",
    "section4.jpg",
    "section5.jpg"
};

// Lighting Controls
#declare LightSpacing     = 12.5;       // Distance between overhead fixtures (yards)
#declare LightIntensity   = 1.1;        // Brightness of each fixture
#declare FixtureColor     = rgb <1.0, 0.98, 0.92>; // Warm neutral light
#declare UseCameraFill    = true;       // Soft traveling fill light attached to camera
#declare UseAtmosphereFog = true;       // Subtle depth fog down the 500-yard run

// ==============================================================================
// CAMERA SETUP
// ==============================================================================
// Dead center horizontally (X = 0) and vertically (Y = 0) inside the tunnel.
// Looking straight ahead along +Z.

#ifndef (CamZ)
    #ifdef (clock)
        // Travels through the entire tunnel as clock goes 0.0 -> 1.0
        #declare CamZ = clock * TotalLength;
    #else
        // Static frame default: 5 yards into Section 1
        #declare CamZ = 5.0;
    #endif
#end

camera {
    perspective
    location <0.0, 0.0, CamZ>
    look_at  <0.0, 0.0, CamZ + 50.0>
    angle    65.0                           // Natural human walking field of view
    right    x * (image_width / image_height)
    up       y
}

// Optional camera fill light (guarantees no dark spots around the viewer)
#if (UseCameraFill)
light_source {
    <0.0, 0.0, CamZ>,
    color rgb 0.18
    shadowless
}
#end

// Subtle depth fog over the 500-yard span
#if (UseAtmosphereFog)
fog {
    distance TotalLength * 1.2
    color rgb <0.015, 0.018, 0.025>
}
#end

// ==============================================================================
// TUNNEL SECTION MACRO
// ==============================================================================
#macro TunnelSection(ZStart, ZLength, ImageFileName)
cylinder {
    <0, 0, 0>, <0, 1, 0>, TunnelRadius
    open
    hollow
    texture {
        pigment {
            image_map {
                jpeg ImageFileName
                map_type 2          // Cylindrical mapping
                interpolate 2       // Smooth bilinear filtering
            }
            // Scale along Y to control lengthwise tiling
            scale <1, 1.0 / RepeatLengthwise, 1>
            // Invert X so the image is NOT mirrored when viewed from INSIDE
            scale <-1, 1, 1>
            // Rotate around cylinder axis to align seam
            rotate <0, SeamAngle, 0>
        }
        finish {
            ambient 0.12            // Keeps distant tunnel walls visible
            diffuse 0.85
            specular 0.25           // Subtle surface sheen
            roughness 0.04
        }
    }
    scale <1, ZLength, 1>
    rotate <90, 0, 0>               // Rotate Y axis into +Z axis
    translate <0, 0, ZStart>
}
#end

// ==============================================================================
// BUILD 5 TUNNEL SECTIONS
// ==============================================================================
union {
    #for (i, 0, NumSections - 1)
        #declare SecStart = i * SectionLength;
        object {
            TunnelSection(SecStart, SectionLength, ImageFiles[i])
        }
    #end
}

// End-cap at the far end of Section 5 (Z = 500 yards)
disc {
    <0, 0, TotalLength>, <0, 0, 1>, TunnelRadius
    pigment { color rgb <0.02, 0.02, 0.03> }
    finish { ambient 0.1 diffuse 0.2 }
}

// ==============================================================================
// OVERHEAD LIGHTING SYSTEM (Well-lit throughout the 500 yards)
// ==============================================================================
#declare FixtureRadius = 0.08;
#declare FixtureLength = 1.2;
#declare LightY = TunnelRadius - 0.25;      // Just below the tunnel ceiling
#declare NumLights = int(TotalLength / LightSpacing);

union {
    #for (k, 1, NumLights)
        #declare LightZ = k * LightSpacing;

        // 1. Point Light Source with realistic falloff
        light_source {
            <0.0, LightY, LightZ>,
            color FixtureColor * LightIntensity
            fade_distance LightSpacing * 1.1
            fade_power 2
            shadowless
        }

        // 2. Physical Glowing Luminaire (visible down the tunnel)
        cylinder {
            <0, LightY, LightZ - FixtureLength/2>,
            <0, LightY, LightZ + FixtureLength/2>,
            FixtureRadius
            pigment { color FixtureColor }
            finish {
                ambient 1.5                 // Self-illuminated appearance
                diffuse 0.0
            }
            no_shadow
        }

        // 3. Ceiling mounting bracket
        cylinder {
            <0, LightY, LightZ>,
            <0, TunnelRadius, LightZ>,
            FixtureRadius * 0.4
            pigment { color rgb <0.2, 0.2, 0.2> }
            finish { diffuse 0.6 ambient 0.1 }
        }
    #end
}