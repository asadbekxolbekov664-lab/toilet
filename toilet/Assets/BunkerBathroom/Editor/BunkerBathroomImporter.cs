using UnityEditor;
using UnityEngine;

// Import rules for the FBX files written by Blender/build_bunker_bathroom.py.
//  - Environment: meters, no cameras/lights/animation, lightmap UVs, static flags.
//  - Collision:   every COL_* mesh becomes a BoxCollider; renderers are stripped.
public class BunkerBathroomImporter : AssetPostprocessor
{
    const string EnvFile = "BunkerBathroom_Environment.fbx";
    const string ColFile = "BunkerBathroom_Collision.fbx";

    bool IsEnvironment => assetPath.EndsWith(EnvFile);
    bool IsCollision => assetPath.EndsWith(ColFile);

    void OnPreprocessModel()
    {
        if (!IsEnvironment && !IsCollision)
            return;
        // Only on first import, so manual changes in the Inspector are kept.
        if (!assetImporter.importSettingsMissing)
            return;

        var mi = (ModelImporter)assetImporter;
        mi.globalScale = 1f;
        mi.useFileScale = true;
        mi.bakeAxisConversion = false;
        mi.importCameras = false;
        mi.importLights = false;
        mi.importVisibility = false;
        mi.importBlendShapes = false;
        mi.importAnimation = false;
        mi.animationType = ModelImporterAnimationType.None;
        mi.meshCompression = ModelImporterMeshCompression.Off;
        mi.isReadable = false;
        mi.optimizeMeshPolygons = true;
        mi.optimizeMeshVertices = true;
        mi.importNormals = ModelImporterNormals.Import;
        mi.importTangents = ModelImporterTangents.CalculateMikk;
        mi.addCollider = false;
        mi.generateSecondaryUV = IsEnvironment;
        mi.materialImportMode = IsEnvironment
            ? ModelImporterMaterialImportMode.ImportViaMaterialDescription
            : ModelImporterMaterialImportMode.None;
    }

    void OnPostprocessModel(GameObject root)
    {
        if (IsCollision)
        {
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!mf.name.StartsWith("COL_") || mf.sharedMesh == null)
                    continue;
                var bounds = mf.sharedMesh.bounds;
                var box = mf.gameObject.AddComponent<BoxCollider>();
                box.center = bounds.center;
                box.size = bounds.size;
                var mr = mf.GetComponent<MeshRenderer>();
                if (mr != null)
                    Object.DestroyImmediate(mr);
                Object.DestroyImmediate(mf);
            }
        }
        else if (IsEnvironment)
        {
            const StaticEditorFlags staticFlags =
                StaticEditorFlags.ContributeGI | StaticEditorFlags.OccluderStatic |
                StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic |
                StaticEditorFlags.ReflectionProbeStatic;
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                if (t.GetComponent<MeshRenderer>() == null)
                    continue;
                // Doors keep their hinge pivot and stay non-static so they can be animated.
                bool movable = t.name.EndsWith("_Door") || t.name.EndsWith("_Leaf");
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, movable ? 0 : staticFlags);
            }
        }
    }
}
