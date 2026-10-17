const mapElement = document.getElementById("classroom-map");

if (mapElement && window.L) {
    const latitudeField = document.getElementById("id_latitude");
    const longitudeField = document.getElementById("id_longitude");
    const radiusField = document.getElementById("id_radius_m");
    const radiusSlider = document.getElementById("radius-slider");
    const saveButton = document.getElementById("save-location");
    const status = document.getElementById("map-status");
    const readout = document.getElementById("coordinate-readout");
    const center = [Number(mapElement.dataset.latitude), Number(mapElement.dataset.longitude)];
    const map = L.map(mapElement).setView(center, mapElement.dataset.hasLocation === "true" ? 18 : 15);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    let marker = null;
    let circle = null;

    function syncRadiusValue() {
        const radius = Number(radiusSlider.value || 100);
        const safeRadius = Number.isFinite(radius) ? radius : 100;
        radiusSlider.value = String(safeRadius);
        radiusField.value = String(safeRadius);
        document.getElementById("radius-readout").textContent = `${safeRadius} m`;
        return safeRadius;
    }

    function updateCircle(position) {
        const radius = syncRadiusValue();
        if (!circle) {
            circle = L.circle(position, {
                radius,
                color: "#bd4c32",
                weight: 2,
                fillColor: "#d76545",
                fillOpacity: 0.18,
            }).addTo(map);
        } else {
            circle.setLatLng(position);
            circle.setRadius(radius);
        }
    }

    function syncFields(position) {
        latitudeField.value = position.lat.toFixed(7);
        longitudeField.value = position.lng.toFixed(7);
        syncRadiusValue();
        readout.textContent = `${position.lat.toFixed(5)}, ${position.lng.toFixed(5)}`;
        status.textContent = "Location set";
        saveButton.disabled = false;

        if (!marker) {
            marker = L.marker(position, { draggable: true }).addTo(map);
            marker.on("drag", () => updateCircle(marker.getLatLng()));
            marker.on("dragend", () => syncFields(marker.getLatLng()));
        } else {
            marker.setLatLng(position);
        }
        updateCircle(position);
    }

    map.on("click", (event) => syncFields(event.latlng));
    radiusSlider.addEventListener("input", () => {
        syncRadiusValue();
        if (marker) updateCircle(marker.getLatLng());
    });

    if (mapElement.dataset.hasLocation === "true") {
        syncRadiusValue();
        syncFields(L.latLng(center[0], center[1]));
    } else {
        syncRadiusValue();
    }

    window.addEventListener("load", () => map.invalidateSize());
}