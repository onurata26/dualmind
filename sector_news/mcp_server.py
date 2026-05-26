import sys
import json
import traceback
from gather_brand_data import gather_all_sources, generate_report_pipeline

def log(message):
    """Logs a message to stderr so it doesn't corrupt the MCP stdin/stdout channel."""
    sys.stderr.write(f"[MCP Server] {message}\n")
    sys.stderr.flush()

def handle_initialize(req_id, params):
    log("Handling 'initialize' request...")
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "Brand-Context-MCP-Server",
                "version": "1.0.0"
            }
        }
    }

def handle_tools_list(req_id):
    log("Handling 'tools/list' request...")
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": [
                {
                    "name": "fetch_raw_sources",
                    "description": "Scrapes and gathers raw news, publications, and forum discussions from PwC, Deloitte, Şikayetvar, Ekşi Sözlük, Reddit, and NewsAPI for the requested brand/category.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "brand": {
                                "type": "string",
                                "description": "The brand name to research (e.g. 'Starbucks', 'Getir', 'Trendyol')"
                            },
                            "category": {
                                "type": "string",
                                "description": "The category of the brand (e.g. 'coffee', 'delivery', 'e-commerce')"
                            },
                            "region": {
                                "type": "string",
                                "description": "The region, default is 'TR'",
                                "default": "TR"
                            },
                            "sector": {
                                "type": "string",
                                "description": "Optional sector name to expand search (e.g. 'Perakende', 'Tüketici Ürünleri')"
                            }
                        },
                        "required": ["brand", "category"]
                    }
                },
                {
                    "name": "generate_report",
                    "description": "Gathers raw data for the brand/company from all sources (PwC, Deloitte, Şikayetvar, Ekşi Sözlük, Reddit, NewsAPI) and synthesizes it with an LLM into the required structured consumer-valence JSON report.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "brand": {
                                "type": "string",
                                "description": "The brand name to research (e.g. 'Starbucks')"
                            },
                            "category": {
                                "type": "string",
                                "description": "The category of the brand (e.g. 'coffee')"
                            },
                            "region": {
                                "type": "string",
                                "description": "The region, default is 'TR'",
                                "default": "TR"
                            },
                            "sector": {
                                "type": "string",
                                "description": "Optional sector name to expand search"
                            }
                        },
                        "required": ["brand", "category"]
                    }
                }
            ]
        }
    }

def handle_tools_call(req_id, params):
    name = params.get("name")
    arguments = params.get("arguments", {})
    
    log(f"Handling 'tools/call' request for tool: '{name}'...")
    
    brand = arguments.get("brand")
    category = arguments.get("category")
    region = arguments.get("region", "TR")
    sector = arguments.get("sector")
    
    if not brand or not category:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32602,
                "message": "Missing required arguments: 'brand' and 'category' are required."
            }
        }
        
    try:
        if name == "fetch_raw_sources":
            raw_data = gather_all_sources(brand, category, region, sector)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(raw_data, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            }
            
        elif name == "generate_report":
            report, output_path = generate_report_pipeline(brand, category, region, sector)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(report, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: Tool '{name}' does not exist."
                }
            }
            
    except Exception as e:
        err_msg = traceback.format_exc()
        log(f"Error executing tool '{name}': {err_msg}")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32603,
                "message": f"Internal error during execution: {str(e)}"
            }
        }

def main():
    log("Server starting up...")
    
    # Set sys.stdout to flush on every write
    # We must be careful not to output standard print messages to sys.stdout
    # only strict JSON-RPC structures
    
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
                
            log(f"Received raw message: {line.strip()[:150]}...")
            
            try:
                message = json.loads(line.strip())
            except Exception as e:
                log(f"Failed to parse incoming line as JSON: {str(e)}")
                continue
                
            method = message.get("method")
            req_id = message.get("id")
            
            response = None
            
            if method == "initialize":
                response = handle_initialize(req_id, message.get("params", {}))
            elif method == "notifications/initialized":
                log("Received initialized notification from client.")
                continue
            elif method == "tools/list":
                response = handle_tools_list(req_id)
            elif method == "tools/call":
                response = handle_tools_call(req_id, message.get("params", {}))
            elif req_id is not None:
                # Handle unknown method with request ID
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: '{method}'"
                    }
                }
                
            if response:
                response_str = json.dumps(response, ensure_ascii=False)
                sys.stdout.write(response_str + "\n")
                sys.stdout.flush()
                log(f"Sent response: {response_str[:150]}...")
                
    except Exception as e:
        log(f"Fatal error in main loop: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
