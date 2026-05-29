import tkinter as tk
from tkinter import ttk
from tkintermapview import TkinterMapView


class MapWindow:
    """
    Displays selected journeys on a map.
    Expects coords_by_journey = { journey_id: [(lat, lon), (lat, lon), ...] }
    """

    def __init__(self, parent, coords_by_journey):
        self.coords = coords_by_journey

        self.window = tk.Toplevel(parent)
        self.window.title("Journey Map")
        self.window.geometry("900x650")

        self.build_ui()
        self.draw_journeys()

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------
    def build_ui(self):
        # Map widget
        self.map_widget = TkinterMapView(self.window, width=900, height=600, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)

        # Default view (NZ)
        self.map_widget.set_position(-36.8485, 174.7633)  # Auckland
        self.map_widget.set_zoom(10)

        # Legend
        legend = ttk.Label(self.window, text="Each journey is shown in a different color  |  Gap markers: orange = dropout start, green = signal resumed")
        legend.pack(pady=5)

    # ------------------------------------------------------------
    # DRAW JOURNEYS
    # ------------------------------------------------------------
    def draw_journeys(self):
        if not self.coords:
            return

        # Color cycle for multiple journeys
        colors = [
            "red", "blue", "green", "orange", "purple",
            "cyan", "magenta", "yellow", "pink", "brown"
        ]
        color_index = 0

        for jid, points in self.coords.items():
            if len(points) < 2:
                continue

            color = colors[color_index % len(colors)]
            color_index += 1

            # Extract (lat, lon) pairs for the path — points may be 2- or 3-tuples
            latlon = [(p[0], p[1]) for p in points]

            # Draw polyline
            self.map_widget.set_path(latlon, color=color, width=3)

            # Start marker
            self.map_widget.set_marker(latlon[0][0], latlon[0][1], text=f"Start {jid}")

            # End marker
            self.map_widget.set_marker(latlon[-1][0], latlon[-1][1], text=f"End {jid}")

            # Gap boundary markers for synthetic sections
            self._draw_gap_markers(points)

    def _draw_gap_markers(self, points):
        """Place orange/green markers at boundaries of synthetic sections."""
        if not points or len(points[0]) < 3:
            return  # No synthetic info available

        in_synthetic = False
        for i, p in enumerate(points):
            lat, lon, is_synthetic = p[0], p[1], p[2]

            if is_synthetic and not in_synthetic:
                # Transition: real -> synthetic (dropout start)
                self.map_widget.set_marker(lat, lon, text="Dropout start", marker_color_circle="orange", marker_color_outside="darkorange")
                in_synthetic = True
            elif not is_synthetic and in_synthetic:
                # Transition: synthetic -> real (signal resumed)
                self.map_widget.set_marker(lat, lon, text="Signal resumed", marker_color_circle="green", marker_color_outside="darkgreen")
                in_synthetic = False
