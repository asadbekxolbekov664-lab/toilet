using UnityEngine;
using UnityEngine.InputSystem;

// Minimal first-person controller for walk-testing the bunker bathroom.
// WASD move, Shift run, Space jump, mouse look, Esc frees the cursor, click recaptures.
// On Start it snaps to the PLAYER_START empty exported from Blender and faces PLAYER_LOOK_TARGET.
[RequireComponent(typeof(CharacterController))]
public class SimpleFirstPersonController : MonoBehaviour
{
    public Transform cameraPivot;
    public float walkSpeed = 2.2f;
    public float runSpeed = 4.5f;
    public float lookSensitivity = 0.1f;
    public float gravity = -15f;
    public float jumpHeight = 0.9f;

    [Header("Spawn")]
    public bool snapToSpawnOnStart = true;
    public string spawnPointName = "PLAYER_START";
    public string lookTargetName = "PLAYER_LOOK_TARGET";

    CharacterController controller;
    float pitch;
    float verticalVelocity;

    void Awake()
    {
        controller = GetComponent<CharacterController>();
    }

    void Start()
    {
        if (snapToSpawnOnStart)
            MoveToSpawn();
        SetCursorLocked(true);
    }

    public void MoveToSpawn()
    {
        var spawn = GameObject.Find(spawnPointName);
        if (spawn == null)
        {
            Debug.LogWarning($"SimpleFirstPersonController: '{spawnPointName}' not found in the scene.");
            return;
        }
        controller.enabled = false;
        transform.position = spawn.transform.position + Vector3.up * 0.02f;
        var look = GameObject.Find(lookTargetName);
        if (look != null)
        {
            var dir = look.transform.position - spawn.transform.position;
            dir.y = 0f;
            if (dir.sqrMagnitude > 1e-4f)
                transform.rotation = Quaternion.LookRotation(dir.normalized, Vector3.up);
        }
        controller.enabled = true;
        pitch = 0f;
        verticalVelocity = 0f;
    }

    void Update()
    {
        var kb = Keyboard.current;
        var mouse = Mouse.current;
        if (kb == null || mouse == null)
            return;

        if (kb.escapeKey.wasPressedThisFrame)
            SetCursorLocked(false);
        else if (mouse.leftButton.wasPressedThisFrame)
            SetCursorLocked(true);

        if (Cursor.lockState == CursorLockMode.Locked)
        {
            Vector2 delta = mouse.delta.ReadValue() * lookSensitivity;
            transform.Rotate(0f, delta.x, 0f);
            pitch = Mathf.Clamp(pitch - delta.y, -85f, 85f);
            if (cameraPivot != null)
                cameraPivot.localEulerAngles = new Vector3(pitch, 0f, 0f);
        }

        Vector2 input = Vector2.zero;
        if (kb.wKey.isPressed) input.y += 1f;
        if (kb.sKey.isPressed) input.y -= 1f;
        if (kb.dKey.isPressed) input.x += 1f;
        if (kb.aKey.isPressed) input.x -= 1f;
        Vector3 move = transform.right * input.x + transform.forward * input.y;
        if (move.sqrMagnitude > 1f)
            move.Normalize();
        float speed = kb.leftShiftKey.isPressed ? runSpeed : walkSpeed;

        if (controller.isGrounded && verticalVelocity < 0f)
            verticalVelocity = -2f;
        if (controller.isGrounded && kb.spaceKey.wasPressedThisFrame)
            verticalVelocity = Mathf.Sqrt(jumpHeight * -2f * gravity);
        verticalVelocity += gravity * Time.deltaTime;

        controller.Move((move * speed + Vector3.up * verticalVelocity) * Time.deltaTime);
    }

    static void SetCursorLocked(bool locked)
    {
        Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
        Cursor.visible = !locked;
    }
}
