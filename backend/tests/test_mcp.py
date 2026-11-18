"""
Comprehensive MCP 2026-07-28 Protocol & Gateway Tests
"""
from fastapi import status


def test_mcp_jsonrpc_initialize(client):
    """Test standard MCP protocol initialize handshake."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    res = client.post("/api/v1/mcp", json=payload)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert "result" in data
    assert data["result"]["protocolVersion"] == "2026-07-28"
    assert data["result"]["serverInfo"]["name"] == "phoenix-mcp-server"


def test_mcp_tools_list_jsonrpc(client):
    """Test tools/list via JSON-RPC returns all 10 core PHOENIX capabilities."""
    payload = {
        "jsonrpc": "2.0",
        "id": "req-tools",
        "method": "tools/list",
        "params": {}
    }
    res = client.post("/api/v1/mcp", json=payload)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    tools = data["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    expected = [
        "phoenix.inspect_project",
        "phoenix.analyze_project",
        "phoenix.diagnose_incident",
        "phoenix.generate_patch",
        "phoenix.validate_patch",
        "phoenix.get_patch_diff",
        "phoenix.get_project_health",
        "phoenix.get_repair_history",
        "phoenix.request_approval",
        "phoenix.generate_report"
    ]
    for exp in expected:
        assert exp in tool_names, f"Expected tool '{exp}' in tools/list"


def test_mcp_resources_and_read(client):
    """Test listing and reading resources."""
    # List resources via JSON-RPC
    res = client.post("/api/v1/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "resources/list"})
    assert res.status_code == status.HTTP_200_OK
    resources = res.json()["result"]["resources"]
    assert any(r["uri"] == "phoenix://system/health" for r in resources)

    # Read system health resource
    read_res = client.post(
        "/api/v1/mcp",
        json={"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": "phoenix://system/health"}}
    )
    assert read_res.status_code == status.HTTP_200_OK
    contents = read_res.json()["result"]["contents"]
    assert len(contents) > 0
    assert "Groq" in contents[0]["text"]


def test_mcp_prompts(client):
    """Test listing and retrieving prompts."""
    # List prompts
    res = client.post("/api/v1/mcp", json={"jsonrpc": "2.0", "id": 4, "method": "prompts/list"})
    assert res.status_code == status.HTTP_200_OK
    prompts = res.json()["result"]["prompts"]
    prompt_names = [p["name"] for p in prompts]
    assert "diagnose_incident" in prompt_names
    assert "review_patch" in prompt_names

    # Get prompt
    get_res = client.post(
        "/api/v1/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 5,
            "method": "prompts/get",
            "params": {"name": "diagnose_incident", "arguments": {"incident_id": "test-inc-1"}}
        }
    )
    assert get_res.status_code == status.HTTP_200_OK
    messages = get_res.json()["result"]["messages"]
    assert len(messages) >= 2
    assert any("test-inc-1" in m["content"]["text"] for m in messages)


def test_mcp_rest_endpoints(client, admin_token):
    """Test REST discovery endpoints for UI integration."""
    # REST tools
    res = client.get("/api/v1/mcp/tools")
    assert res.status_code == status.HTTP_200_OK
    assert len(res.json()) >= 10

    # REST resources
    res_resources = client.get("/api/v1/mcp/resources")
    assert res_resources.status_code == status.HTTP_200_OK
    assert len(res_resources.json()) >= 4

    # REST prompts
    res_prompts = client.get("/api/v1/mcp/prompts")
    assert res_prompts.status_code == status.HTTP_200_OK
    assert len(res_prompts.json()) >= 4

    # REST external servers
    res_servers = client.get("/api/v1/mcp/servers")
    assert res_servers.status_code == status.HTTP_200_OK
    servers = res_servers.json()
    assert any(s["id"] == "github-mcp" for s in servers)


def test_mcp_policy_gating_unauthorized(client, dev_token):
    """Test that administrative MCP tools reject unprivileged callers."""
    payload = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "phoenix.request_approval",
            "arguments": {"patch_id": "dummy-patch-id"}
        }
    }
    # Dev role cannot directly invoke ADMINISTRATIVE tool
    res = client.post(
        "/api/v1/mcp",
        json=payload,
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert res.status_code == status.HTTP_200_OK
    result = res.json()["result"]
    assert result["isError"] is True
    assert "Permission denied" in result["content"][0]["text"]
