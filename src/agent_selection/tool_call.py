from typing import Any, Dict


class ToolCall:
    def __init__(self):
        pass
    
    def search(self, query: str) -> Dict[Any, Any]:
        # semantic search
        pass
    
    def tool_calling(self, tool_name: str, params: Dict[Any, Any]) -> Dict[Any, Any]:
        pass