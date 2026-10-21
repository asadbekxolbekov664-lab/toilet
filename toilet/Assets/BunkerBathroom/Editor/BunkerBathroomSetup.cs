using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

// Tools > Bunker Bathroom menu.
//  1. Create URP Materials  - builds URP/Lit materials from BunkerBathroom_Materials.json
//                             (written by the Blender script) and remaps the FBX onto them.
//  2. Build Scene           - drops environment + collision into the open scene, adds lights at
//                             the LIGHT_* markers, a reflection probe and a first-person player
//                             at PLAYER_START.
public static class BunkerBathroomSetup
{
    const string Root = "Assets/BunkerBathroom";
    const string EnvPath = Root + "/Models/BunkerBathroom_Environment.fbx";
    const string ColPath = Root + "/Models/BunkerBathroom_Collision.fbx";
    const string JsonPath = Root + "/Models/BunkerBathroom_Materials.json";
    const string MatDir = Root + "/Materials";

    static readonly Color FluorescentColor = new Color(0.86f, 0.94f, 1f);

    [System.Serializable]
    class MatDef
    {
        public string name;
        public float[] color;
        public float metallic;
        public float smoothness;
        public float emission;
    }

    [System.Serializable]
    class MatTable
    {
        public MatDef[] materials;
    }

    [MenuItem("Tools/Bunker Bathroom/1. Create URP Materials")]
    public static void CreateMaterials()
    {
        var json = AssetDatabase.LoadAssetAtPath<TextAsset>(JsonPath);
        if (json == null)
        {
            Debug.LogError($"Bunker Bathroom: {JsonPath} not found. Run the Blender script first.");
            return;
        }
        var table = JsonUtility.FromJson<MatTable>(json.text);
        if (!AssetDatabase.IsValidFolder(MatDir))
            AssetDatabase.CreateFolder(Root, "Materials");

        var shader = Shader.Find("Universal Render Pipeline/Lit");
        var importer = AssetImporter.GetAtPath(EnvPath) as ModelImporter;
        foreach (var d in table.materials)
        {
            string path = $"{MatDir}/{d.name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(shader) { name = d.name };
                AssetDatabase.CreateAsset(mat, path);
            }
            // Blender stores linear colours; Material.SetColor expects sRGB.
            var color = new Color(d.color[0], d.color[1], d.color[2]).gamma;
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Metallic", d.metallic);
            mat.SetFloat("_Smoothness", d.smoothness);
            if (d.emission > 0f)
            {
                mat.EnableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", color * 2.5f);
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
            }
            EditorUtility.SetDirty(mat);
            if (importer != null)
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), d.name), mat);
        }
        AssetDatabase.SaveAssets();
        if (importer != null)
            importer.SaveAndReimport();
        Debug.Log($"Bunker Bathroom: {table.materials.Length} URP materials created in {MatDir}.");
    }

    [MenuItem("Tools/Bunker Bathroom/2. Build Scene (adds to open scene)")]
    public static void BuildScene()
    {
        CreateMaterials();
        var envAsset = AssetDatabase.LoadAssetAtPath<GameObject>(EnvPath);
        var colAsset = AssetDatabase.LoadAssetAtPath<GameObject>(ColPath);
        if (envAsset == null || colAsset == null)
        {
            Debug.LogError("Bunker Bathroom: FBX files not found in " + Root + "/Models.");
            return;
        }

        var old = GameObject.Find("BunkerBathroom");
        if (old != null)
            Undo.DestroyObjectImmediate(old);

        var root = new GameObject("BunkerBathroom");
        Undo.RegisterCreatedObjectUndo(root, "Build Bunker Bathroom");
        var env = (GameObject)PrefabUtility.InstantiatePrefab(envAsset, root.transform);
        PrefabUtility.InstantiatePrefab(colAsset, root.transform);

        var lights = new GameObject("Lights").transform;
        lights.SetParent(root.transform, false);
        foreach (var t in env.GetComponentsInChildren<Transform>(true))
        {
            if (t.name.StartsWith("LIGHT_CEIL"))
                AddLight(t, lights, LightType.Spot, 4f, 7f, true);
            else if (t.name.StartsWith("LIGHT_WALL"))
                AddLight(t, lights, LightType.Point, 0.5f, 2.5f, false);
        }

        var bounds = new Bounds(env.transform.position, Vector3.zero);
        foreach (var r in env.GetComponentsInChildren<Renderer>())
            bounds.Encapsulate(r.bounds);
        var probeGo = new GameObject("ReflectionProbe");
        probeGo.transform.SetParent(root.transform, false);
        probeGo.transform.position = new Vector3(bounds.center.x, 1.6f, bounds.center.z);
        var probe = probeGo.AddComponent<ReflectionProbe>();
        probe.mode = ReflectionProbeMode.Realtime;
        probe.refreshMode = ReflectionProbeRefreshMode.OnAwake;
        probe.timeSlicingMode = ReflectionProbeTimeSlicingMode.NoTimeSlicing;
        probe.size = bounds.size;
        probe.center = bounds.center - probeGo.transform.position;
        probe.boxProjection = true;

        RenderSettings.ambientMode = AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.16f, 0.17f, 0.19f);

        // Underground room: a sun would only leak through shadow gaps.
        foreach (var l in FindInScene<Light>())
        {
            if (l.type == LightType.Directional && l.gameObject.activeSelf)
            {
                Undo.RecordObject(l.gameObject, "Disable sun");
                l.gameObject.SetActive(false);
            }
        }

        CreatePlayer(env.transform);
        EditorSceneManager.MarkSceneDirty(root.scene);
        Selection.activeGameObject = root;
        Debug.Log("Bunker Bathroom: scene built. Press Play to walk around.");
    }

    static void AddLight(Transform marker, Transform parent, LightType type, float intensity, float range, bool shadows)
    {
        var go = new GameObject(marker.name.Replace("LIGHT_", "Light_"));
        go.transform.SetParent(parent, false);
        go.transform.position = marker.position;
        go.transform.rotation = Quaternion.Euler(90f, 0f, 0f);   // straight down
        var light = go.AddComponent<Light>();
        light.type = type;
        light.color = FluorescentColor;
        light.intensity = intensity;
        light.range = range;
        if (type == LightType.Spot)
        {
            light.spotAngle = 150f;
            light.innerSpotAngle = 90f;
        }
        light.shadows = shadows ? LightShadows.Soft : LightShadows.None;
    }

    static void CreatePlayer(Transform envRoot)
    {
        var spawn = FindDeep(envRoot, "PLAYER_START");
        var look = FindDeep(envRoot, "PLAYER_LOOK_TARGET");
        var camStart = FindDeep(envRoot, "PLAYER_CAMERA_START");
        if (spawn == null)
        {
            Debug.LogWarning("Bunker Bathroom: PLAYER_START not found in the environment FBX.");
            return;
        }
        float eye = camStart != null ? camStart.position.y - spawn.position.y : 1.65f;

        GameObject player = null;
        foreach (var fpc in FindInScene<SimpleFirstPersonController>())
            player = fpc.gameObject;

        if (player == null)
        {
            player = new GameObject("Player") { tag = "Player" };
            Undo.RegisterCreatedObjectUndo(player, "Create player");
            var cc = player.AddComponent<CharacterController>();
            cc.height = 1.8f;
            cc.radius = 0.3f;
            cc.center = new Vector3(0f, 0.9f, 0f);
            cc.stepOffset = 0.3f;
            cc.skinWidth = 0.03f;

            var camGo = new GameObject("PlayerCamera") { tag = "MainCamera" };
            camGo.transform.SetParent(player.transform, false);
            camGo.transform.localPosition = new Vector3(0f, eye, 0f);
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.05f;
            cam.fieldOfView = 70f;
            camGo.AddComponent<AudioListener>();

            var controller = player.AddComponent<SimpleFirstPersonController>();
            controller.cameraPivot = camGo.transform;

            foreach (var other in FindInScene<Camera>())
            {
                if (other != cam && other.gameObject.activeSelf)
                {
                    Undo.RecordObject(other.gameObject, "Disable camera");
                    other.gameObject.SetActive(false);
                }
            }
        }

        Undo.RecordObject(player.transform, "Place player");
        player.transform.position = spawn.position;
        if (look != null)
        {
            var dir = look.position - spawn.position;
            dir.y = 0f;
            if (dir.sqrMagnitude > 1e-4f)
                player.transform.rotation = Quaternion.LookRotation(dir.normalized, Vector3.up);
        }
    }

    static Transform FindDeep(Transform root, string name)
    {
        foreach (var t in root.GetComponentsInChildren<Transform>(true))
            if (t.name == name)
                return t;
        return null;
    }

    static List<T> FindInScene<T>() where T : Component
    {
        var list = new List<T>();
        foreach (var go in SceneManager.GetActiveScene().GetRootGameObjects())
            list.AddRange(go.GetComponentsInChildren<T>(true));
        return list;
    }
}
