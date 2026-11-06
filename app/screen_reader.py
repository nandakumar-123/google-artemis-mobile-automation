import re
import os
import defusedxml.ElementTree as ET
from typing import List, Dict, Optional, Tuple, Any
from app.adb_manager import ADBManager
from app.config import SCREENSHOTS_DIR

class UIElement:
    def __init__(self, text: str, content_desc: str, resource_id: str, class_name: str, bounds: Tuple[int, int, int, int], clickable: bool):
        self.text = text
        self.content_desc = content_desc
        self.resource_id = resource_id
        self.class_name = class_name
        self.bounds = bounds  # (left, top, right, bottom)
        self.clickable = clickable

    @property
    def center(self) -> Tuple[int, int]:
        left, top, right, bottom = self.bounds
        return ((left + right) // 2, (top + bottom) // 2)

    @property
    def width(self) -> int:
        return max(0, self.bounds[2] - self.bounds[0])

    @property
    def height(self) -> int:
        return max(0, self.bounds[3] - self.bounds[1])

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "content_desc": self.content_desc,
            "resource_id": self.resource_id,
            "class_name": self.class_name,
            "bounds": list(self.bounds),
            "center": list(self.center),
            "width": self.width,
            "height": self.height,
            "clickable": self.clickable
        }

class ScreenReader:
    def __init__(self, adb_manager: ADBManager):
        self.adb = adb_manager

    def capture_screenshot(self, filename: Optional[str] = None) -> Optional[str]:
        if not filename:
            from datetime import datetime
            filename = f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        local_path = str(SCREENSHOTS_DIR / filename)
        success = self.adb.take_screenshot(local_path)
        if success and os.path.exists(local_path):
            return local_path
        return None

    def dump_and_parse_ui(self) -> List[UIElement]:
        xml_path = str(SCREENSHOTS_DIR / "hierarchy_temp.xml")
        success = self.adb.dump_hierarchy(xml_path)
        if not success or not os.path.exists(xml_path):
            return []
        
        elements = []
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            elements = self._parse_nodes(root)
        except Exception as e:
            print(f"Error parsing UI XML: {e}")
        finally:
            if os.path.exists(xml_path):
                try:
                    os.remove(xml_path)
                except Exception:
                    pass
        return elements

    def _parse_bounds(self, bounds_str: str) -> Optional[Tuple[int, int, int, int]]:
        # format: [left,top][right,bottom] e.g. [0,0][1080,2400]
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
        if match:
            return tuple(int(x) for x in match.groups()) # type: ignore
        return None

    def _parse_nodes(self, node) -> List[UIElement]:
        elements = []
        bounds_str = node.attrib.get("bounds", "")
        bounds = self._parse_bounds(bounds_str)
        text = node.attrib.get("text", "").strip()
        desc = node.attrib.get("content-desc", "").strip()
        res_id = node.attrib.get("resource-id", "").strip()
        cls_name = node.attrib.get("class", "").strip()
        clickable = node.attrib.get("clickable", "false").lower() == "true"

        if bounds and (text or desc or clickable or res_id):
            elements.append(UIElement(
                text=text,
                content_desc=desc,
                resource_id=res_id,
                class_name=cls_name,
                bounds=bounds,
                clickable=clickable
            ))

        for child in node:
            elements.extend(self._parse_nodes(child))
        return elements

    def get_screen_summary(self) -> Dict[str, Any]:
        elements = self.dump_and_parse_ui()
        visible_texts = []
        clickable_items = []
        
        for el in elements:
            label = el.text or el.content_desc
            if label:
                visible_texts.append(label)
            if el.clickable or label:
                clickable_items.append(el.to_dict())

        return {
            "visible_texts": list(dict.fromkeys(visible_texts)),
            "interactive_elements": clickable_items[:50]  # cap to top 50 to avoid prompt bloat
        }

    def find_element(
        self,
        text: Optional[str] = None,
        content_desc: Optional[str] = None,
        resource_id: Optional[str] = None,
        class_name: Optional[str] = None,
        clickable_only: bool = False,
        prefer_clickable: bool = True,
        match_index: int = 0,
        elements: Optional[List[UIElement]] = None
    ) -> Optional[UIElement]:
        """
        Dynamically finds matching UIElement based on clickable status, exact text,
        content descriptions, resource IDs, class names, and bounds.
        Supports exact match first, then substring/case-insensitive match.
        Prefers clickable elements and valid bounded regions.
        """
        all_elements = elements if elements is not None else self.dump_and_parse_ui()
        if not all_elements:
            return None

        # Filter out invalid or zero-area bounds
        valid_elements = [el for el in all_elements if el.area > 0]
        if clickable_only:
            valid_elements = [el for el in valid_elements if el.clickable]

        if not valid_elements:
            return None

        norm_text = text.strip().lower() if text else None
        norm_desc = content_desc.strip().lower() if content_desc else None
        norm_res = resource_id.strip().lower() if resource_id else None
        norm_cls = class_name.strip().lower() if class_name else None

        def _sort_key(el: UIElement) -> Tuple[int, int]:
            # Prefer clickable (0 before 1), then prefer reasonable interactive size
            click_rank = 0 if el.clickable else (1 if not prefer_clickable else 2)
            # Penalize huge full-screen overlay bounds when matching specific items
            area_penalty = 1 if el.area > 2000000 else 0
            return (click_rank, area_penalty)

        # Pass 1: Exact matches across text, content_desc, or resource_id
        exact_matches = []
        for el in valid_elements:
            el_text = el.text.strip().lower()
            el_desc = el.content_desc.strip().lower()
            el_res = el.resource_id.strip().lower()
            el_cls = el.class_name.strip().lower()

            matched = True
            if norm_text and norm_text != el_text:
                matched = False
            if norm_desc and norm_desc != el_desc:
                matched = False
            if norm_res and norm_res != el_res and not el_res.endswith(f"/{norm_res}"):
                matched = False
            if norm_cls and norm_cls != el_cls:
                matched = False

            if matched:
                exact_matches.append(el)

        if exact_matches:
            if prefer_clickable:
                exact_matches.sort(key=_sort_key)
            idx = min(max(0, match_index), len(exact_matches) - 1)
            return exact_matches[idx]

        # Pass 2: Substring matches
        sub_matches = []
        for el in valid_elements:
            el_text = el.text.strip().lower()
            el_desc = el.content_desc.strip().lower()
            el_res = el.resource_id.strip().lower()
            el_cls = el.class_name.strip().lower()

            matched = True
            if norm_text and norm_text not in el_text:
                matched = False
            if norm_desc and norm_desc not in el_desc:
                matched = False
            if norm_res and norm_res not in el_res:
                matched = False
            if norm_cls and norm_cls not in el_cls:
                matched = False

            if matched:
                sub_matches.append(el)

        if sub_matches:
            if prefer_clickable:
                sub_matches.sort(key=_sort_key)
            idx = min(max(0, match_index), len(sub_matches) - 1)
            return sub_matches[idx]

        return None

    def wait_for_ui_condition(
        self,
        condition_func,
        timeout: float = 10.0,
        poll_interval: float = 0.8
    ) -> Tuple[bool, Any]:
        """
        Polls dump_and_parse_ui until condition_func(elements) returns a truthy value or timeout expires.
        """
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            elements = self.dump_and_parse_ui()
            res = condition_func(elements)
            if res:
                return True, res
            time.sleep(poll_interval)
        return False, None


