// ============================================================================
//  CRYSTAL ATELIER  -  a ray-tracing showcase
//  Faceted glassware, jewel gems, and a geometric crystal chandelier.
//  Every crystal is REAL faceted geometry (platonic solids as plane
//  intersections), so facets genuinely bend and split the light.
//
//  Render:   povray +Ishowcase_crystal_atelier.pov +W1600 +H900 +A0.3 +AM2 +R3
//  Fast look:  set DRAFT = 1 below  (skips photons + dispersion, cheap GI)
//  Hero look:  leave DRAFT = 0      (caustics + colour dispersion + full GI)
// ============================================================================
#version 3.7;

#declare DRAFT = 1;          // <-- 1 = fast preview,  0 = full beauty render

// ---- quality knobs derived from DRAFT ----
#if (DRAFT)
  #declare DISP_SAMPLES = 2;
  #declare DISP_AMT     = 1.0;
#else
  #declare DISP_SAMPLES = 7;
  #declare DISP_AMT     = 1.035;
#end

global_settings {
  assumed_gamma 1.0
  max_trace_level 18
  #if (DRAFT = 0)
    photons { count 260000 autostop 0 jitter 0.35 }
  #end
  radiosity {
    brightness 1
    #if (DRAFT)
      count 40 error_bound 0.8 recursion_limit 1 pretrace_end 0.04
    #else
      count 160 error_bound 0.32 nearest_count 8
      recursion_limit 2 pretrace_start 0.08 pretrace_end 0.01
    #end
  }
}

// ============================================================================
//  FACETED SOLIDS  -  each is the intersection of planes whose normals point
//  at the face centres.  Golden-ratio normals give true platonic crystals.
// ============================================================================
#declare PHI = (1 + sqrt(5)) / 2;

// 20 dodecahedron vertices  ==  the 20 FACE normals of an ICOSAHEDRON
#declare IcoFaceN = array[20] {
  < 1, 1, 1>, < 1, 1,-1>, < 1,-1, 1>, < 1,-1,-1>,
  <-1, 1, 1>, <-1, 1,-1>, <-1,-1, 1>, <-1,-1,-1>,
  <0,  1/PHI,  PHI>, <0,  1/PHI, -PHI>, <0, -1/PHI,  PHI>, <0, -1/PHI, -PHI>,
  < 1/PHI,  PHI,0>, < 1/PHI, -PHI,0>, <-1/PHI,  PHI,0>, <-1/PHI, -PHI,0>,
  < PHI,0, 1/PHI>, < PHI,0,-1/PHI>, <-PHI,0, 1/PHI>, <-PHI,0,-1/PHI>
}

// 12 icosahedron vertices  ==  the 12 FACE normals of a DODECAHEDRON
#declare DodecaFaceN = array[12] {
  <0, 1, PHI>, <0, 1,-PHI>, <0,-1, PHI>, <0,-1,-PHI>,
  <1, PHI,0>, <1,-PHI,0>, <-1, PHI,0>, <-1,-PHI,0>,
  <PHI,0,1>, <PHI,0,-1>, <-PHI,0,1>, <-PHI,0,-1>
}

// 8 octahedron face normals
#declare OctaN = array[8] {
  <1,1,1>,<1,1,-1>,<1,-1,1>,<1,-1,-1>,<-1,1,1>,<-1,1,-1>,<-1,-1,1>,<-1,-1,-1>
}

// build a convex faceted solid from a normal list, inradius D
#macro FacetSolid(Nrm, Cnt, D)
  intersection {
    #local i = 0;
    #while (i < Cnt)
      plane { vnormalize(Nrm[i]), D }
      #local i = i + 1;
    #end
  }
#end

// ============================================================================
//  MATERIALS
// ============================================================================
// clear lead-crystal: sharp facets, fresnel edge glint, faint cool absorption,
// and chromatic dispersion that splatters rainbow caustics.
#declare M_Crystal =
material {
  texture {
    pigment { color rgbf <0.97, 0.99, 1.0, 0.95> }
    finish {
      ambient 0 diffuse 0.03
      specular 0.95 roughness 0.0009
      reflection { 0.06, 1.0 fresnel on }
      conserve_energy
    }
  }
  interior {
    ior 1.52
    caustics 1.0
    dispersion DISP_AMT dispersion_samples DISP_SAMPLES
    fade_distance 2.4 fade_power 1001 fade_color <0.70, 0.86, 1.0>
  }
}

// coloured gem material factory  (Tint = the colour the glass keeps)
#macro GemMat(Tint)
  material {
    texture {
      pigment { color rgbf <Tint.red, Tint.green, Tint.blue, 0.88> }
      finish {
        ambient 0 diffuse 0.04
        specular 0.98 roughness 0.0008
        reflection { 0.08, 1.0 fresnel on }
        conserve_energy
      }
    }
    interior {
      ior 1.62
      caustics 1.0
      dispersion DISP_AMT dispersion_samples DISP_SAMPLES
      fade_distance 1.1 fade_power 1001 fade_color Tint * 0.65
    }
  }
#end

// warm brushed brass for the chandelier frame
#declare M_Brass =
texture {
  pigment { color rgb <0.80, 0.63, 0.30> }
  finish {
    ambient 0 diffuse 0.22 brilliance 2
    metallic
    specular 0.85 roughness 0.012
    reflection { 0.42 metallic }
  }
}

// polished dark marble for the display pedestal
#declare M_Stone =
texture {
  pigment {
    granite
    color_map {
      [0.0 color rgb <0.04, 0.04, 0.05>]
      [0.5 color rgb <0.10, 0.10, 0.12>]
      [0.8 color rgb <0.15, 0.14, 0.16>]
      [1.0 color rgb <0.03, 0.03, 0.04>]
    }
    scale 1.2
  }
  finish {
    ambient 0 diffuse 0.14
    specular 0.35 roughness 0.02
    reflection { 0.10, 0.45 fresnel on }
    conserve_energy
  }
}

// display pedestal: foot + column + overhanging table top with a brass rim
#declare Pedestal =
object {
  union {
    cylinder { <0,0,0>,    <0,0.12,0>, 2.00 }      // base foot
    cylinder { <0,0,0>,    <0,1.42,0>, 1.75 }      // column
    cylinder { <0,1.42,0>, <0,1.62,0>, 2.45 }      // table top
  }
  texture { M_Stone }
  interior { ior 1.5 }
}

// ============================================================================
//  REUSABLE CRYSTAL PIECES
// ============================================================================
// classic chandelier drop: an octahedron stretched into a tall bipyramid
#declare CrystalDrop =
object {
  FacetSolid(OctaN, 8, 1)
  scale <0.17, 0.36, 0.17>
  material { M_Crystal }
  photons { target reflection on refraction on }
}

// a standing cut crystal with a flat base (icosahedron, stretched + clipped)
#macro StandingCrystal(Mat)
  intersection {
    object { FacetSolid(IcoFaceN, 20, 1) scale <0.60, 1.45, 0.60> }
    plane { -y, 0 }                       // flat base sits on the floor
    material { Mat }
    photons { target reflection on refraction on }
  }
#end

// a loose gem (choose solid), flat-based so it rests on the floor
#macro LooseGem(Which, R, Mat)
  intersection {
    #if (Which = 0) object { FacetSolid(IcoFaceN, 20, 1) scale R } #end
    #if (Which = 1) object { FacetSolid(DodecaFaceN, 12, 1) scale R } #end
    #if (Which = 2) object { FacetSolid(OctaN, 8, 1) scale R } #end
    plane { -y, 0 }
    material { Mat }
    photons { target reflection on refraction on }
  }
#end

// ============================================================================
//  THE FACETED CRYSTAL BOWL  -  hollow dodecahedron, flat base, open rim
// ============================================================================
#declare CrystalBowl =
object {
  intersection {
    plane { -y, 0 }                                   // flat base at floor
    difference {
      FacetSolid(DodecaFaceN, 12, 1.00)               // outer shell
      intersection {                                   // hollow cavity...
        FacetSolid(DodecaFaceN, 12, 0.84)
        plane { -y, -0.30 }                            // ...only above the base
      }
      plane { y, 0.58 }                                // cut the top open
    }
  }
  material { M_Crystal }
  photons { target reflection on refraction on }
}

// ============================================================================
//  GEOMETRIC CRYSTAL CHANDELIER
// ============================================================================
#declare Chandelier =
union {
  cylinder { <0, 9.6, 0>, <0, 7.2, 0>, 0.045 texture { M_Brass } }   // suspension rod
  torus { 1.10, 0.050 translate y*7.2 texture { M_Brass } }         // upper ring
  torus { 2.30, 0.065 translate y*6.2 texture { M_Brass } }         // lower ring

  // brass struts: rod -> upper ring -> lower ring
  #local k = 0;
  #while (k < 6)
    #local a = k * pi / 3;
    cylinder { <0,7.2,0>, <1.10*cos(a),7.2,1.10*sin(a)>, 0.032 texture { M_Brass } }
    cylinder { <1.10*cos(a),7.2,1.10*sin(a)>, <2.30*cos(a),6.2,2.30*sin(a)>, 0.032 texture { M_Brass } }
    #local k = k + 1;
  #end

  // outer curtain of hanging crystal drops around the lower ring
  #local Ndrops = 20;
  #local n = 0;
  #while (n < Ndrops)
    #local a  = n * 2 * pi / Ndrops;
    #local px = 2.30 * cos(a);
    #local pz = 2.30 * sin(a);
    cylinder { <px,6.2,pz>, <px,5.62,pz>, 0.011 texture { M_Brass } }   // wire
    object { CrystalDrop translate <px, 5.42, pz> }
    #local n = n + 1;
  #end

  // inner ring of smaller drops
  #local n = 0;
  #while (n < 8)
    #local a  = n * pi / 4 + 0.25;
    #local px = 1.10 * cos(a);
    #local pz = 1.10 * sin(a);
    cylinder { <px,7.2,pz>, <px,6.78,pz>, 0.010 texture { M_Brass } }
    object { CrystalDrop scale 0.78 translate <px, 6.62, pz> }
    #local n = n + 1;
  #end

  // central hero crystal, lit from within
  object {
    FacetSolid(IcoFaceN, 20, 1) scale 0.55
    material { M_Crystal }
    translate y*6.05
    photons { target reflection on refraction on }
  }
  // the "bulb" - a small warm emitter nested inside the central crystal
  sphere { <0,6.05,0>, 0.20 pigment { rgb <1.0,0.94,0.78> } finish { ambient 3.2 diffuse 0 } }
}

// ============================================================================
//  SCENE ASSEMBLY
// ============================================================================
// --- polished dark floor: a near-black mirror so caustics + reflections sing
plane {
  y, 0
  texture {
    pigment { color rgb <0.015, 0.016, 0.022> }
    finish {
      ambient 0 diffuse 0.08
      specular 0.25 roughness 0.015
      reflection { 0.10, 0.55 fresnel on }
      conserve_energy
    }
  }
  interior { ior 1.5 }
}

// --- warm gallery backdrop (vertical gradient sky)
sky_sphere {
  pigment {
    gradient y
    color_map {
      [0.0 color rgb <0.03, 0.03, 0.05>]
      [0.5 color rgb <0.10, 0.09, 0.12>]
      [1.0 color rgb <0.22, 0.18, 0.20>]
    }
    scale 2 translate -1
  }
}

// --- the display pedestal
#declare PT = 1.62;                 // pedestal top height (where glassware rests)
object { Pedestal }

// --- glassware on the pedestal
object { CrystalBowl scale 1.35 translate <0.2, PT, 0> }

// a few jewel gems resting inside the bowl
object { LooseGem(2, 0.28, GemMat(rgb <0.85,0.10,0.18>)) rotate y*20 translate <0.05, PT+0.42, 0.10> }
object { LooseGem(0, 0.26, GemMat(rgb <0.10,0.55,0.95>)) rotate y*50 translate <0.42, PT+0.42, -0.18> }
object { LooseGem(1, 0.25, GemMat(rgb <0.95,0.75,0.10>)) rotate y*80 translate <-0.25, PT+0.42, -0.25> }

// a tall standing crystal centrepiece just behind the bowl
object { StandingCrystal(M_Crystal) rotate y*15 translate <-1.35, PT, 0.9> }

// a couple of gems resting on the pedestal top beside the bowl
object { LooseGem(1, 0.30, GemMat(rgb <0.15,0.80,0.45>)) rotate y*35  translate < 1.55, PT, -0.4> }
object { LooseGem(2, 0.30, GemMat(rgb <0.70,0.20,0.95>)) rotate y*120 translate <-1.60, PT, -0.9> }

// loose gems on the mirror floor, catching the chandelier caustics
object { LooseGem(0, 0.40, GemMat(rgb <0.95,0.35,0.05>)) rotate y*25  translate < 3.4, 0, -1.2> }
object { LooseGem(2, 0.42, GemMat(rgb <0.90,0.08,0.55>)) rotate y*60  translate < 3.0, 0,  2.3> }
object { LooseGem(1, 0.38, GemMat(rgb <0.05,0.70,0.80>)) rotate y*100 translate <-3.0, 0, -2.2> }
object { LooseGem(0, 0.44, GemMat(rgb <0.80,0.75,0.10>)) rotate y*160 translate <-3.8, 0,  1.6> }

// --- the chandelier overhead (lowered to close the gap to the glassware)
object { Chandelier translate <0, -1.1, 0> }

// ============================================================================
//  LIGHTING
// ============================================================================
// chandelier bulb: warm, soft, and the main photon source for caustics
light_source {
  <0, 4.95, 0>
  color rgb <1.0, 0.90, 0.72> * 2.2
  fade_distance 6 fade_power 2
  area_light x*0.5, z*0.5, 4, 4 adaptive 1 jitter circular orient
  photons { refraction on reflection on }
}

// warm key light, upper front-left - soft shadows, drives edge caustics
light_source {
  <-9, 11, -8>
  color rgb <1.0, 0.95, 0.85> * 1.1
  area_light x*3, z*3, 5, 5 adaptive 1 jitter circular
  photons { refraction on reflection on }
}

// cool fill from the right so shadow sides keep some colour
light_source {
  <10, 7, -3>
  color rgb <0.55, 0.68, 0.95> * 0.5
  shadowless
}

// ============================================================================
//  CAMERA  -  three-quarter hero view
// ============================================================================
camera {
  perspective
  location <7.6, 4.3, -9.6>
  look_at  <0.0, 3.4, 0.0>
  angle 54
}
