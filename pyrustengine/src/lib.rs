use engine::negamax;
use engine::structs::EvalOptions;
use hexchess::Hexchess;
use serde_json::{json, Value};
use std::ffi::{c_char, CStr, CString};
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::time::{SystemTime, UNIX_EPOCH};

#[no_mangle]
pub extern "C" fn hexchess_engine_execute(
    command: *const c_char,
    options_json: *const c_char,
) -> *mut c_char {
    let payload = match catch_unwind(AssertUnwindSafe(|| execute_ffi(command, options_json))) {
        Ok(payload) => payload,
        Err(_) => json!({
            "ok": false,
            "error": {
                "message": "Rust engine panicked while handling the command"
            }
        }),
    };

    json_to_c_string(payload)
}

#[no_mangle]
pub extern "C" fn hexchess_engine_string_free(value: *mut c_char) {
    if value.is_null() {
        return;
    }

    unsafe {
        let _ = CString::from_raw(value);
    }
}

fn execute_ffi(command: *const c_char, options_json: *const c_char) -> Value {
    let command = match read_c_string(command) {
        Ok(value) => value,
        Err(message) => return error_payload(&message),
    };

    let options_json = match read_c_string(options_json) {
        Ok(value) => value,
        Err(message) => return error_payload(&message),
    };

    match execute_command(&command, &options_json) {
        Ok(response) => json!({
            "ok": true,
            "response": response,
        }),
        Err(message) => error_payload(&message),
    }
}

fn execute_command(command: &str, options_json: &str) -> Result<Value, String> {
    let options = parse_options(options_json)?;

    match command {
        "hexchess/ping" => Ok(json!({
            "now": current_timestamp_millis(),
        })),
        "hexchess/evaluate" => evaluate(&options),
        _ => Err(format!("Unknown engine command: {}", command)),
    }
}

fn evaluate(options: &Value) -> Result<Value, String> {
    let position = options
        .get("position")
        .and_then(Value::as_str)
        .ok_or_else(|| "invalid position: expected string".to_string())?;

    let depth = options
        .get("depth")
        .and_then(Value::as_u64)
        .ok_or_else(|| "invalid depth: expected integer".to_string())?;

    if depth > u8::MAX as u64 {
        return Err(format!("invalid depth: expected integer <= {}", u8::MAX));
    }

    let hexchess = Hexchess::parse(position).map_err(|message| format!("invalid position: {}", message))?;
    let response = negamax::search(&hexchess, depth as u8, &EvalOptions::default());

    serde_json::to_value(response).map_err(|message| format!("failed to serialize response: {}", message))
}

fn parse_options(source: &str) -> Result<Value, String> {
    if source.trim().is_empty() {
        return Ok(json!({}));
    }

    serde_json::from_str::<Value>(source).map_err(|message| format!("invalid options json: {}", message))
}

fn read_c_string(value: *const c_char) -> Result<String, String> {
    if value.is_null() {
        return Ok(String::new());
    }

    let c_str = unsafe { CStr::from_ptr(value) };

    c_str
        .to_str()
        .map(|value| value.to_owned())
        .map_err(|_| "input contained invalid UTF-8".to_string())
}

fn current_timestamp_millis() -> u128 {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(duration) => duration.as_millis(),
        Err(_) => 0,
    }
}

fn error_payload(message: &str) -> Value {
    json!({
        "ok": false,
        "error": {
            "message": message,
        }
    })
}

fn json_to_c_string(payload: Value) -> *mut c_char {
    let serialized = match serde_json::to_string(&payload) {
        Ok(value) => value,
        Err(message) => {
            format!(
                "{{\"ok\":false,\"error\":{{\"message\":\"failed to serialize bridge payload: {}\"}}}}",
                message
            )
        }
    };

    match CString::new(serialized) {
        Ok(value) => value.into_raw(),
        Err(_) => CString::new(
            "{\"ok\":false,\"error\":{\"message\":\"bridge payload contained an interior null byte\"}}",
        )
        .expect("static fallback CString must be valid")
        .into_raw(),
    }
}
