from app.infra.runpod import RunPodClient, _iter_ports, _unwrap_pod_payload


def test_iter_ports_runtime_is_string():
    data = {"runtime": "RUNNING", "ports": [{"privatePort": 22, "publicPort": 2222, "ip": "1.2.3.4"}]}
    ports = _iter_ports(data)
    assert len(ports) == 1
    assert ports[0]["ip"] == "1.2.3.4"


def test_parse_pod_runtime_string_no_crash():
    client = RunPodClient.__new__(RunPodClient)
    data = {
        "name": "test-pod",
        "desiredStatus": "RUNNING",
        "runtime": "RUNNING",
        "publicIp": "203.0.113.1",
        "machine": "RTX 4090",
    }
    info = client._parse_pod("abc123", data)
    assert info.public_ip == "203.0.113.1"
    assert info.name == "test-pod"
    assert info.gpu_type == "RTX 4090"


def test_unwrap_nested_pod():
    raw = {"pod": {"id": "x", "publicIp": "10.0.0.1", "name": "p1"}}
    inner = _unwrap_pod_payload(raw, "x")
    assert inner["publicIp"] == "10.0.0.1"


def test_parse_pod_graphql_ports():
    client = RunPodClient.__new__(RunPodClient)
    data = {
        "name": "gpu-pod",
        "desiredStatus": "RUNNING",
        "runtime": {
            "ports": [
                {"privatePort": 22, "publicPort": 22022, "ip": "198.51.100.2", "isIpPublic": True}
            ]
        },
        "machine": {"gpuDisplayName": "A100"},
    }
    info = client._parse_pod("id1", data)
    assert info.public_ip == "198.51.100.2"
    assert info.ssh_port == 22022
    assert info.gpu_type == "A100"
