"""Viewer control tools for the ViewerAgent

These tools generate viewer operation specifications that are sent to the frontend
to control the Autodesk Viewer. The frontend executes these operations using ViewerAPI.
"""
from typing import List, Dict, Any, Optional


class ViewerTools:
    """Tools for controlling the Autodesk Viewer through natural language"""

    def __init__(self, model_metadata: Optional[Dict] = None):
        """
        Initialize ViewerTools

        Args:
            model_metadata: Optional pre-loaded model metadata (properties, hierarchy)
                          Can be used for element lookups without viewer interaction
        """
        self.model_metadata = model_metadata or {}

    # ============= SELECTION TOOLS =============

    def select_elements(
        self,
        db_ids: Optional[List[int]] = None,
        by_property: Optional[Dict[str, str]] = None,
        by_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Select elements in the viewer

        Args:
            db_ids: List of database IDs to select
            by_property: Dict with 'property' and 'value' keys to search by
            by_name: Search elements by name pattern

        Returns:
            Viewer operation specification
        """
        if db_ids:
            return {
                "operation": "select",
                "params": {"dbIds": db_ids},
                "description": f"Selected {len(db_ids)} element(s)"
            }
        elif by_property:
            return {
                "operation": "selectByProperty",
                "params": {
                    "property": by_property.get("property", "name"),
                    "value": by_property.get("value", "")
                },
                "description": f"Selecting elements where {by_property.get('property')} = {by_property.get('value')}"
            }
        elif by_name:
            return {
                "operation": "selectByProperty",
                "params": {"property": "name", "value": by_name},
                "description": f"Selecting elements with name matching '{by_name}'"
            }
        return {"error": "Must specify db_ids, by_property, or by_name"}

    def clear_selection(self) -> Dict[str, Any]:
        """Clear the current selection"""
        return {
            "operation": "clearSelection",
            "params": {},
            "description": "Cleared selection"
        }

    # ============= VISIBILITY TOOLS =============

    def isolate_elements(self, db_ids: List[int]) -> Dict[str, Any]:
        """
        Isolate specified elements (hide everything else)

        Args:
            db_ids: List of database IDs to isolate
        """
        return {
            "operation": "isolate",
            "params": {"dbIds": db_ids},
            "description": f"Isolated {len(db_ids)} element(s)"
        }

    def hide_elements(self, db_ids: List[int]) -> Dict[str, Any]:
        """
        Hide specified elements

        Args:
            db_ids: List of database IDs to hide
        """
        return {
            "operation": "hide",
            "params": {"dbIds": db_ids},
            "description": f"Hidden {len(db_ids)} element(s)"
        }

    def show_elements(self, db_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Show elements (all if no db_ids specified)

        Args:
            db_ids: Optional list of database IDs to show, or None to show all
        """
        if db_ids:
            return {
                "operation": "show",
                "params": {"dbIds": db_ids},
                "description": f"Showing {len(db_ids)} element(s)"
            }
        return {
            "operation": "showAll",
            "params": {},
            "description": "Showing all elements"
        }

    def show_all(self) -> Dict[str, Any]:
        """Show all elements and clear isolation"""
        return {
            "operation": "showAll",
            "params": {},
            "description": "Showing all elements"
        }

    # ============= CAMERA TOOLS =============

    def zoom_to_fit(self, db_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Zoom camera to fit elements in view

        Args:
            db_ids: Optional list of database IDs to fit, or None to fit entire model
        """
        return {
            "operation": "fitToView",
            "params": {"dbIds": db_ids or []},
            "description": f"Zoomed to fit {len(db_ids) if db_ids else 'all'} element(s)"
        }

    def set_camera_view(self, preset: str) -> Dict[str, Any]:
        """
        Set camera to a preset view

        Args:
            preset: One of 'front', 'back', 'top', 'bottom', 'left', 'right',
                   'iso', 'iso_front', 'iso_back'
        """
        valid_presets = ['front', 'back', 'top', 'bottom', 'left', 'right', 'iso', 'iso_front', 'iso_back']
        preset_lower = preset.lower()

        if preset_lower not in valid_presets:
            return {"error": f"Invalid preset. Must be one of: {', '.join(valid_presets)}"}

        return {
            "operation": "setCameraPreset",
            "params": {"preset": preset_lower},
            "description": f"Set camera to {preset_lower} view"
        }

    def set_camera_position(
        self,
        position: List[float],
        target: List[float],
        up: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Set exact camera position and target

        Args:
            position: Camera position [x, y, z]
            target: Look-at target [x, y, z]
            up: Optional up vector [x, y, z], defaults to [0, 0, 1]
        """
        if len(position) != 3 or len(target) != 3:
            return {"error": "Position and target must be [x, y, z] arrays"}

        return {
            "operation": "setCamera",
            "params": {
                "position": position,
                "target": target,
                "up": up or [0, 0, 1]
            },
            "description": "Set custom camera position"
        }

    # ============= SECTION TOOLS =============

    def create_section_plane(
        self,
        plane: str,
        offset: float = 0
    ) -> Dict[str, Any]:
        """
        Create a section cutting plane

        Args:
            plane: Plane axis - 'X', 'Y', or 'Z'
            offset: Offset from model center
        """
        plane_upper = plane.upper()
        if plane_upper not in ['X', 'Y', 'Z']:
            return {"error": "Plane must be 'X', 'Y', or 'Z'"}

        return {
            "operation": "createSection",
            "params": {"plane": plane_upper, "offset": offset},
            "description": f"Created {plane_upper}-axis section plane at offset {offset}"
        }

    def clear_sections(self) -> Dict[str, Any]:
        """Remove all section planes"""
        return {
            "operation": "clearSection",
            "params": {},
            "description": "Cleared all section planes"
        }

    # ============= EXPLODE TOOLS =============

    def explode_model(self, scale: float = 1.0) -> Dict[str, Any]:
        """
        Explode the model to see internal components

        Args:
            scale: Explode scale (0 = assembled, 1-3 = exploded)
        """
        # Clamp scale between 0 and 3
        clamped_scale = max(0, min(scale, 3))

        return {
            "operation": "explode",
            "params": {"scale": clamped_scale},
            "description": f"Set explode scale to {clamped_scale}"
        }

    def reset_explode(self) -> Dict[str, Any]:
        """Reset explode (set scale to 0)"""
        return {
            "operation": "explode",
            "params": {"scale": 0},
            "description": "Reset explode (assembled view)"
        }

    # ============= MEASUREMENT TOOLS =============

    def start_measurement(self, measure_type: str = "distance") -> Dict[str, Any]:
        """
        Start a measurement tool

        Args:
            measure_type: Type of measurement - 'distance', 'angle', or 'area'
        """
        valid_types = ['distance', 'angle', 'area']
        type_lower = measure_type.lower()

        if type_lower not in valid_types:
            return {"error": f"Invalid measurement type. Must be one of: {', '.join(valid_types)}"}

        return {
            "operation": "measure",
            "params": {"type": type_lower},
            "description": f"Started {type_lower} measurement tool"
        }

    def clear_measurements(self) -> Dict[str, Any]:
        """Clear all measurements"""
        return {
            "operation": "clearMeasurements",
            "params": {},
            "description": "Cleared all measurements"
        }

    # ============= MARKUP/ANNOTATION TOOLS =============

    def add_markup(
        self,
        markup_type: str,
        text: Optional[str] = None,
        position: Optional[Dict[str, float]] = None,
        style: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add annotation/markup to the view

        Args:
            markup_type: Type of markup - 'text', 'arrow', 'circle', 'rectangle', 'freehand', 'cloud', 'polyline'
            text: Text content for text markups
            position: Screen position {x, y}
            style: Style options {color, strokeWidth, fontSize}
        """
        valid_types = ['text', 'arrow', 'circle', 'rectangle', 'freehand', 'cloud', 'polyline']
        type_lower = markup_type.lower()

        if type_lower not in valid_types:
            return {"error": f"Invalid markup type. Must be one of: {', '.join(valid_types)}"}

        return {
            "operation": "addMarkup",
            "params": {
                "type": type_lower,
                "text": text,
                "position": position,
                "style": style
            },
            "description": f"Added {type_lower} markup"
        }

    def clear_markups(self) -> Dict[str, Any]:
        """Clear all markups"""
        return {
            "operation": "clearMarkups",
            "params": {},
            "description": "Cleared all markups"
        }

    # ============= WALKTHROUGH TOOLS =============

    def start_walkthrough(
        self,
        waypoints: List[Dict[str, List[float]]]
    ) -> Dict[str, Any]:
        """
        Start camera walkthrough animation

        Args:
            waypoints: List of waypoints, each with:
                - position: [x, y, z] camera position
                - target: [x, y, z] look-at target
                - duration: (optional) milliseconds to reach this waypoint
        """
        if not waypoints or len(waypoints) < 2:
            return {"error": "Walkthrough requires at least 2 waypoints"}

        # Validate waypoints
        for i, wp in enumerate(waypoints):
            if 'position' not in wp or 'target' not in wp:
                return {"error": f"Waypoint {i} must have 'position' and 'target'"}
            if len(wp['position']) != 3 or len(wp['target']) != 3:
                return {"error": f"Waypoint {i} position and target must be [x, y, z]"}

        return {
            "operation": "startWalkthrough",
            "params": {"waypoints": waypoints},
            "description": f"Started walkthrough with {len(waypoints)} waypoints"
        }

    def stop_walkthrough(self) -> Dict[str, Any]:
        """Stop walkthrough animation"""
        return {
            "operation": "stopWalkthrough",
            "params": {},
            "description": "Stopped walkthrough"
        }

    # ============= PROPERTY TOOLS =============

    def get_element_properties(self, db_id: int) -> Dict[str, Any]:
        """
        Get properties of an element

        Args:
            db_id: Database ID of the element
        """
        return {
            "operation": "getProperties",
            "params": {"dbId": db_id},
            "description": f"Getting properties for element {db_id}"
        }

    def search_elements(
        self,
        category: Optional[str] = None,
        property_name: Optional[str] = None,
        value: Optional[str] = None,
        filters: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Search for elements by one or more property filters.

        Args:
            category: Element category (e.g., 'Walls', 'Doors', 'Windows')
            property_name: Property name to search (single filter mode)
            value: Value to match (single filter mode)
            filters: Array of {property, value} dicts for multi-criteria search
        """
        # Build filter list from either filters array or legacy params
        search_filters = []

        if filters and len(filters) > 0:
            search_filters = filters
        else:
            # Legacy single-filter mode
            if category:
                search_filters.append({"property": "Category", "value": category})
            if property_name and value:
                search_filters.append({"property": property_name, "value": value})
            elif value and not category:
                search_filters.append({"property": None, "value": value})

        if not search_filters:
            return {"error": "Must provide search filters, value, or category"}

        descriptions = [f"{f.get('property', 'any')}={f['value']}" for f in search_filters]

        return {
            "operation": "searchByProperty",
            "params": {
                "filters": search_filters
            },
            "description": f"Searching for elements matching: {', '.join(descriptions)}"
        }

    def get_model_properties(
        self,
        search_term: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Request the frontend to return available property names and values
        from a sample element. The frontend will find an element (optionally
        matching search_term) and return its properties.
        """
        return {
            "operation": "getModelProperties",
            "params": {
                "search_term": search_term
            },
            "description": f"Inspecting model properties{' for ' + search_term if search_term else ''}"
        }

    # ============= UTILITY METHODS =============

    def combine_operations(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combine multiple operations into a sequence

        Args:
            operations: List of operation specifications

        Returns:
            List of valid operations (errors filtered out)
        """
        return [op for op in operations if "error" not in op]
