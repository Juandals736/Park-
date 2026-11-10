/* ==========================================================================
   LANDING PAGE PARK+ - MAPA ACTIVO, RUTAS SIN REDIRECCIONAR & PWA
   ========================================================================== */

let landingMap = null;
let parkingMarkers = [];
let userLocationMarker = null;
let userAccuracyCircle = null;
let userCoordinates = null; // { lat, lng }
let activeRouteLayer = null;
let allParkings = [];
let activeVehicleFilter = 'todos';
let searchQuery = '';
let deferredPrompt = null;

document.addEventListener('DOMContentLoaded', () => {
  // 1. Inicializar PWA
  initPWA();

  // 2. Menú móvil
  const mobileToggle = document.getElementById('mobileToggle');
  const landingNavLinks = document.getElementById('landingNavLinks');
  if (mobileToggle && landingNavLinks) {
    mobileToggle.addEventListener('click', () => {
      landingNavLinks.classList.toggle('open');
    });

    landingNavLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        landingNavLinks.classList.remove('open');
      });
    });
  }

  // 3. Mapa interactivo (solo si la vista contiene el contenedor del mapa)
  const mapElement = document.getElementById('landingLeafletMap');
  if (mapElement) {
    initLandingMap();

    const btnLocateMe = document.getElementById('btnLocateMe');
    if (btnLocateMe) {
      btnLocateMe.addEventListener('click', () => {
        requestDeviceLocation(true);
      });
    }

    const btnCancelRoute = document.getElementById('btnCancelRoute');
    if (btnCancelRoute) {
      btnCancelRoute.addEventListener('click', () => {
        cancelarRuta();
      });
    }

    document.querySelectorAll('.filter-chip').forEach(chip => {
      chip.addEventListener('click', function() {
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        activeVehicleFilter = this.getAttribute('data-type');
        filterAndRenderParkings();
      });
    });

    const searchInput = document.getElementById('searchParkingInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase().trim();
        filterAndRenderParkings();
      });
    }

    loadParkingsData();
  }
});

/* --------------------------------------------------------------------------
   1. MAPA LEAFLET SIEMPRE ACTIVO Y VISIBLE
   -------------------------------------------------------------------------- */
function initLandingMap() {
  const mapElement = document.getElementById('landingLeafletMap');
  if (!mapElement) return;

  // Centro por defecto: Pasto / Universidad (1.2136, -77.2811)
  const defaultCenter = [1.2136, -77.2811];

  landingMap = L.map('landingLeafletMap', {
    zoomControl: true,
    scrollWheelZoom: true
  }).setView(defaultCenter, 14);

  // Capa de OpenStreetMap estándar
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(landingMap);

  // IMPORTANTE: Asegurar que el mapa nunca se vea gris ni colapsado
  setTimeout(() => { if (landingMap) landingMap.invalidateSize(); }, 150);
  setTimeout(() => { if (landingMap) landingMap.invalidateSize(); }, 400);
  setTimeout(() => { if (landingMap) landingMap.invalidateSize(); }, 800);
  setTimeout(() => { if (landingMap) landingMap.invalidateSize(); }, 1500);

  window.addEventListener('resize', () => {
    if (landingMap) landingMap.invalidateSize();
  });

  // Re-invalidar tamaño si el usuario hace scroll hacia la sección del mapa
  const mapaSection = document.getElementById('mapa');
  if (mapaSection && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && landingMap) {
          landingMap.invalidateSize();
        }
      });
    }, { threshold: 0.1 });
    observer.observe(mapaSection);
  }
}

/* --------------------------------------------------------------------------
   2. GEOLOCALIZACIÓN DEL DISPOSITIVO (GPS)
   -------------------------------------------------------------------------- */
function requestDeviceLocation(isManualClick = false, callback = null) {
  const btn = document.getElementById('btnLocateMe');
  const banner = document.getElementById('geoStatusBanner');

  if (!navigator.geolocation) {
    showGeoBanner('Tu dispositivo o navegador no soporta geolocalización GPS.', 'warning');
    if (callback) callback(null);
    return;
  }

  if (btn) {
    btn.classList.add('loading');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Localizando tu dispositivo...';
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      const accuracy = position.coords.accuracy;

      userCoordinates = { lat, lng };

      if (btn) {
        btn.classList.remove('loading');
        btn.innerHTML = '<i class="fas fa-check-circle"></i> ¡Ubicación GPS Activa!';
        btn.style.background = 'linear-gradient(135deg, #059669 0%, #047857 100%)';
      }

      setUserLocationOnMap(lat, lng, accuracy);
      calculateDistancesAndSort();
      filterAndRenderParkings();

      const closest = allParkings.length > 0 ? allParkings[0] : null;
      let msg = `📍 ¡GPS Conectado! Parqueaderos ordenados por distancia a tu vehículo.`;
      if (closest && closest.distancia_texto) {
        msg = `📍 ¡GPS Conectado! El parqueadero más cercano (${closest.nombre}) está a solo <strong>${closest.distancia_texto}</strong>.`;
      }
      showGeoBanner(msg, 'success');

      if (callback) callback(userCoordinates);
    },
    (error) => {
      if (btn) {
        btn.classList.remove('loading');
        btn.innerHTML = '<i class="fas fa-location-crosshairs"></i> Ubicarme en el Mapa (GPS)';
      }

      let errDesc = 'Permiso de ubicación denegado o GPS desactivado.';
      if (error.code === error.TIMEOUT) {
        errDesc = 'Tiempo de espera de GPS expirado.';
      }
      if (isManualClick) {
        showGeoBanner(errDesc, 'warning');
      }

      if (callback) callback(null);
    },
    { enableHighAccuracy: true, timeout: 5000, maximumAge: 30000 }
  );
}

function setUserLocationOnMap(lat, lng, accuracy) {
  if (!landingMap) return;

  if (userLocationMarker) landingMap.removeLayer(userLocationMarker);
  if (userAccuracyCircle) landingMap.removeLayer(userAccuracyCircle);

  const userIcon = L.divIcon({
    className: 'custom-user-gps-icon',
    html: `
      <div class="user-gps-marker">
        <div class="user-gps-pulse"></div>
        <div class="user-gps-core"></div>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
  });

  userLocationMarker = L.marker([lat, lng], { icon: userIcon, zIndexOffset: 1000 }).addTo(landingMap);
  userLocationMarker.bindPopup('<strong style="color: #1e3a8a;"><i class="fas fa-street-view"></i> Tu Ubicación GPS</strong>');

  if (accuracy && accuracy < 2000) {
    userAccuracyCircle = L.circle([lat, lng], {
      radius: accuracy,
      color: '#3b82f6',
      fillColor: '#93c5fd',
      fillOpacity: 0.15,
      weight: 1
    }).addTo(landingMap);
  }

  landingMap.flyTo([lat, lng], 15, { duration: 1 });
}

function showGeoBanner(htmlContent, type) {
  const banner = document.getElementById('geoStatusBanner');
  if (!banner) return;
  banner.className = `geo-status-banner ${type}`;
  banner.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i> <div>${htmlContent}</div>`;
  banner.style.display = 'flex';
}

/* --------------------------------------------------------------------------
   3. CÓMO LLEGAR DIRECTO EN EL MAPA (SIN REDIRECCIONAR)
   -------------------------------------------------------------------------- */
window.trazarRutaSinRedireccionar = function(destLat, destLng, destNombre) {
  // Desplazar la vista suavemente al mapa
  const mapSection = document.getElementById('mapa');
  if (mapSection) {
    mapSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  if (landingMap) landingMap.invalidateSize();

  // Si ya tenemos coordenadas GPS del usuario, trazamos inmediatamente
  if (userCoordinates) {
    ejecutarCalculoRuta(userCoordinates.lat, userCoordinates.lng, destLat, destLng, destNombre);
    return;
  }

  // Trazar INMEDIATAMENTE sin demoras desde el punto de referencia de la ciudad
  const fallbackOrigin = [1.2136, -77.2811];
  ejecutarCalculoRuta(fallbackOrigin[0], fallbackOrigin[1], destLat, destLng, destNombre);

  // E intentar afinar la ruta en segundo plano si el dispositivo tiene GPS activo
  requestDeviceLocation(false, (coords) => {
    if (coords) {
      ejecutarCalculoRuta(coords.lat, coords.lng, destLat, destLng, destNombre);
    }
  });
};

function ejecutarCalculoRuta(origLat, origLng, destLat, destLng, destNombre) {
  mostrarPanelRuta(`Trazando ruta a ${destNombre}...`, `Calculando calles y tiempos en tiempo real`, true);

  // Llamada al servicio gratuito y abierto OSRM para trazado de ruta callejera
  const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${origLng},${origLat};${destLng},${destLat}?overview=full&geometries=geojson`;

  fetch(osrmUrl)
    .then(res => res.json())
    .then(data => {
      if (data && data.routes && data.routes.length > 0) {
        const route = data.routes[0];
        // Invertir [lng, lat] de GeoJSON a [lat, lng] de Leaflet
        const coords = route.geometry.coordinates.map(c => [c[1], c[0]]);

        dibujarRutaEnMapa(coords);

        const distKm = (route.distance / 1000).toFixed(1);
        const minutos = Math.max(1, Math.round(route.duration / 60));

        mostrarPanelRuta(
          `Ruta hacia: ${destNombre}`,
          `<i class="fas fa-road text-blue"></i> <strong>${distKm} km</strong> • <i class="fas fa-car text-green"></i> Aprox. <strong>${minutos} min</strong> en vehículo`,
          false
        );
      } else {
        throw new Error('Sin ruta de OSRM');
      }
    })
    .catch(() => {
      // Fallback: trazado de línea directa entre origen y destino si OSRM no responde
      const coords = [[origLat, origLng], [destLat, destLng]];
      dibujarRutaEnMapa(coords);

      const dist = getDistanceFromLatLonInKm(origLat, origLng, destLat, destLng);
      const distTxt = dist < 1 ? `${Math.round(dist * 1000)} m` : `${dist.toFixed(1)} km`;
      const min = Math.max(1, Math.round((dist / 30) * 60));

      mostrarPanelRuta(
        `Ruta directa a ${destNombre}`,
        `<i class="fas fa-road text-blue"></i> <strong>${distTxt}</strong> • <i class="fas fa-car text-green"></i> Aprox. <strong>${min} min</strong>`,
        false
      );
    });
}

function dibujarRutaEnMapa(latlngs) {
  if (!landingMap) return;

  if (activeRouteLayer) {
    landingMap.removeLayer(activeRouteLayer);
  }

  landingMap.invalidateSize();

  activeRouteLayer = L.polyline(latlngs, {
    color: '#2563eb',
    weight: 6,
    opacity: 0.9,
    lineJoin: 'round'
  }).addTo(landingMap);

  landingMap.fitBounds(activeRouteLayer.getBounds(), { padding: [50, 50] });
}

function mostrarPanelRuta(titulo, metricas, isCargando) {
  const panel = document.getElementById('routeOverlayPanel');
  const titleEl = document.getElementById('routeDestTitle');
  const metricsEl = document.getElementById('routeMetricsText');
  if (!panel || !titleEl || !metricsEl) return;

  titleEl.innerHTML = titulo;
  metricsEl.innerHTML = metricas;
  panel.style.display = 'flex';
}

window.cancelarRuta = function() {
  if (activeRouteLayer && landingMap) {
    landingMap.removeLayer(activeRouteLayer);
    activeRouteLayer = null;
  }
  const panel = document.getElementById('routeOverlayPanel');
  if (panel) panel.style.display = 'none';
};

/* --------------------------------------------------------------------------
   4. DISTANCIAS HAVERSINE Y FILTRADO
   -------------------------------------------------------------------------- */
function calculateDistancesAndSort() {
  if (!userCoordinates) return;

  allParkings.forEach(p => {
    if (p.latitud && p.longitud) {
      const distKm = getDistanceFromLatLonInKm(
        userCoordinates.lat,
        userCoordinates.lng,
        p.latitud,
        p.longitud
      );
      p.distancia_km = distKm;
      p.distancia_texto = distKm < 1 ? `${Math.round(distKm * 1000)} m` : `${distKm.toFixed(1)} km`;
    } else {
      p.distancia_km = 999999;
      p.distancia_texto = '';
    }
  });

  allParkings.sort((a, b) => a.distancia_km - b.distancia_km);
}

function getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

const FALLBACK_PARKINGS_LANDING = [
  {
    id: 1,
    nombre: 'Park+ Centro',
    direccion: 'Carrera 24 # 18-42, Centro',
    latitud: 1.195923,
    longitud: -77.292206,
    capacidad_total: 53,
    espacios_disponibles: 18,
    tipo_vehiculo: 'ambos',
    tarifa_hora: 3500,
    estado: 'disponible'
  },
  {
    id: 2,
    nombre: 'Parqueadero Las Cuadras',
    direccion: 'Calle 18 # 31-25, Las Cuadras',
    latitud: 1.218896,
    longitud: -77.296911,
    capacidad_total: 44,
    espacios_disponibles: 14,
    tipo_vehiculo: 'ambos',
    tarifa_hora: 2500,
    estado: 'disponible'
  },
  {
    id: 3,
    nombre: 'Estacionamiento Universidad de Nariño',
    direccion: 'Torobajo, Calle 18',
    latitud: 1.231200,
    longitud: -77.292800,
    capacidad_total: 65,
    espacios_disponibles: 22,
    tipo_vehiculo: 'ambos',
    tarifa_hora: 2000,
    estado: 'disponible'
  },
  {
    id: 4,
    nombre: 'Parqueadero San Andrés',
    direccion: 'Calle 16 # 29-14, San Andrés',
    latitud: 1.212500,
    longitud: -77.282500,
    capacidad_total: 35,
    espacios_disponibles: 6,
    tipo_vehiculo: 'ambos',
    tarifa_hora: 3000,
    estado: 'casi_lleno'
  }
];

function loadParkingsData() {
  // 1. Usar datos incrustados inicialmente
  if (window.INITIAL_PARKINGS && window.INITIAL_PARKINGS.length > 0) {
    allParkings = window.INITIAL_PARKINGS;
    filterAndRenderParkings();
  } else {
    // Si la BD aún no tiene registros, usar datos por defecto inmediatamente para que el mapa nunca esté vacío
    allParkings = FALLBACK_PARKINGS_LANDING;
    filterAndRenderParkings();
  }

  // 2. Refrescar vía API pública
  fetch('/api/public/parqueaderos')
    .then(res => res.json())
    .then(data => {
      if (Array.isArray(data) && data.length > 0) {
        allParkings = data;
      } else if (allParkings.length === 0) {
        allParkings = FALLBACK_PARKINGS_LANDING;
      }
      if (userCoordinates) calculateDistancesAndSort();
      filterAndRenderParkings();
      if (landingMap) landingMap.invalidateSize();
    })
    .catch(() => {
      if (allParkings.length === 0) {
        allParkings = FALLBACK_PARKINGS_LANDING;
        filterAndRenderParkings();
      }
    });
}

function filterAndRenderParkings() {
  if (!landingMap) return;

  // Limpiar marcadores anteriores
  parkingMarkers.forEach(m => landingMap.removeLayer(m));
  parkingMarkers = [];

  const container = document.getElementById('landingParkingCardsContainer');
  if (container) container.innerHTML = '';

  const filtered = allParkings.filter(p => {
    if (activeVehicleFilter !== 'todos') {
      const t = (p.tipo_vehiculo || '').toLowerCase();
      const esAmbos = t === 'ambos' || t === 'mixto';
      if (activeVehicleFilter === 'carro' && !(esAmbos || t.includes('carro') || t.includes('auto'))) return false;
      if (activeVehicleFilter === 'moto' && !(esAmbos || t.includes('moto'))) return false;
    }

    if (searchQuery) {
      const matchName = (p.nombre || '').toLowerCase().includes(searchQuery);
      const matchAddress = (p.direccion || '').toLowerCase().includes(searchQuery);
      if (!matchName && !matchAddress) return false;
    }

    return true;
  });

  if (filtered.length === 0) {
    if (container) {
      container.innerHTML = `
        <div style="text-align: center; padding: 2.5rem 1rem; color: #94a3b8;">
          <i class="fas fa-search" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
          No se encontraron parqueaderos.
        </div>
      `;
    }
    return;
  }

  const bounds = [];
  if (userCoordinates) {
    bounds.push([userCoordinates.lat, userCoordinates.lng]);
  }

  filtered.forEach(p => {
    if (p.latitud && p.longitud) {
      bounds.push([p.latitud, p.longitud]);

      let badgeClass = 'disponible';
      let markerColor = '#10b981';

      if (p.estado === 'casi_lleno') {
        badgeClass = 'casi_lleno';
        markerColor = '#f59e0b';
      } else if (p.estado === 'lleno') {
        badgeClass = 'lleno';
        markerColor = '#ef4444';
      } else if (p.estado === 'cerrado') {
        badgeClass = 'cerrado';
        markerColor = '#64748b';
      }

      const markerHtml = `
        <div style="background-color: ${markerColor}; width: 34px; height: 34px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); border: 2px solid white;">
          <i class="fas fa-parking" style="transform: rotate(45deg); color: white; font-size: 15px;"></i>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'parking-map-marker',
        html: markerHtml,
        iconSize: [34, 34],
        iconAnchor: [17, 34],
        popupAnchor: [0, -32]
      });

      const marker = L.marker([p.latitud, p.longitud], { icon: customIcon }).addTo(landingMap);

      const popupContent = `
        <div style="min-width: 210px; font-family: 'Plus Jakarta Sans', sans-serif;">
          <div style="font-weight: 800; font-size: 1rem; color: #0f172a; margin-bottom: 0.2rem;">${p.nombre}</div>
          <div style="font-size: 0.8rem; color: #64748b; margin-bottom: 0.4rem;"><i class="fas fa-map-marker-alt text-blue"></i> ${p.direccion}</div>
          
          ${p.distancia_texto ? `<div style="display:inline-block; font-size: 0.75rem; background: #eff6ff; color: #1d4ed8; font-weight: 800; padding: 0.2rem 0.5rem; border-radius: 6px; margin-bottom: 0.5rem;"><i class="fas fa-location-arrow"></i> A ${p.distancia_texto}</div>` : ''}

          <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.5rem 0; font-size: 0.82rem; border-top: 1px solid #f1f5f9; padding-top: 0.4rem;">
            <span>Cupos: <strong>${p.espacios_disponibles ?? 'N/A'}</strong> / ${p.capacidad_total ?? 'N/A'}</span>
            <span style="font-weight: 800; color: #059669;">$${Math.round(p.tarifa_hora || 0)}/h</span>
          </div>

          <div style="display: flex; gap: 0.4rem; margin-top: 0.75rem;">
            <button type="button" onclick="trazarRutaSinRedireccionar(${p.latitud}, ${p.longitud}, '${p.nombre.replace(/'/g, "\\'")}')" style="flex: 1; text-align: center; background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; font-size: 0.75rem; font-weight: 700; padding: 0.45rem; border-radius: 8px; cursor: pointer;">
              <i class="fas fa-route"></i> Cómo llegar
            </button>
            <a href="${window.IS_AUTHENTICATED ? '/student/mapa' : '/auth/login'}" style="flex: 1; text-align: center; background: #2563eb; color: white; text-decoration: none; font-size: 0.75rem; font-weight: 700; padding: 0.45rem; border-radius: 8px;">
              Reservar
            </a>
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);
      parkingMarkers.push(marker);

      // Tarjeta en lista
      if (container) {
        const card = document.createElement('div');
        card.className = 'landing-parking-card';
        card.setAttribute('data-id', p.id);

        card.innerHTML = `
          <div class="card-top-row">
            <div class="card-p-name">${p.nombre}</div>
            ${p.distancia_texto ? `<span class="card-p-dist"><i class="fas fa-location-arrow"></i> ${p.distancia_texto}</span>` : ''}
          </div>
          <div class="card-p-address"><i class="fas fa-map-pin text-blue"></i> ${p.direccion}</div>
          <div class="card-p-info">
            <div class="cupos-badge">
              <span class="badge-dot ${badgeClass}"></span>
              <span>${p.espacios_disponibles ?? 0} cupos libres</span>
            </div>
            <div style="font-weight: 800; color: #1e3a8a;">
              $${Math.round(p.tarifa_hora || 0)} <span style="font-size: 0.72rem; font-weight: 500; color: #64748b;">/hr</span>
            </div>
          </div>
          <div class="card-actions-row">
            <button type="button" class="btn-como-llegar-inline" onclick="event.stopPropagation(); trazarRutaSinRedireccionar(${p.latitud}, ${p.longitud}, '${p.nombre.replace(/'/g, "\\'")}')">
              <i class="fas fa-route"></i> Cómo llegar
            </button>
            <a href="${window.IS_AUTHENTICATED ? '/student/mapa' : '/auth/login'}" class="btn-reservar-inline">
              Reservar
            </a>
          </div>
        `;

        card.addEventListener('click', () => {
          document.querySelectorAll('.landing-parking-card').forEach(c => c.classList.remove('selected'));
          card.classList.add('selected');
          landingMap.flyTo([p.latitud, p.longitud], 16, { duration: 0.8 });
          marker.openPopup();
        });

        container.appendChild(card);
      }
    }
  });

  if (bounds.length > 0 && !userCoordinates && !activeRouteLayer) {
    landingMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
  }
}

/* --------------------------------------------------------------------------
   5. PWA (DESCARGA EN MÓVIL)
   -------------------------------------------------------------------------- */
function initPWA() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }

  const installBtnHero = document.getElementById('btnInstallAppHero');
  const installBtnSection = document.getElementById('btnInstallAppSection');
  const mobileBanner = document.getElementById('mobileInstallBanner');
  const btnBannerInstall = document.getElementById('btnBannerInstall');
  const btnBannerClose = document.getElementById('btnBannerClose');

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (window.innerWidth <= 768 && !sessionStorage.getItem('parkplus_dismissed_install')) {
      if (mobileBanner) mobileBanner.style.display = 'flex';
    }
  });

  function triggerInstall() {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then((choiceResult) => {
        if (choiceResult.outcome === 'accepted') {
          if (mobileBanner) mobileBanner.style.display = 'none';
        }
        deferredPrompt = null;
      });
    } else {
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
      if (isIOS) {
        alert("📲 Para instalar Park+ en tu iPhone:\n\n1. Toca el botón 'Compartir' en Safari (icono con flecha arriba).\n2. Selecciona 'Añadir a la pantalla de inicio'.\n\n¡Listo! Tendrás la app en tu pantalla.");
      } else {
        alert("📲 Puedes instalar Park+ desde el menú de opciones de tu navegador (los 3 puntos arriba) seleccionando 'Instalar aplicación' o 'Añadir a pantalla de inicio'.");
      }
    }
  }

  if (installBtnHero) installBtnHero.addEventListener('click', triggerInstall);
  if (installBtnSection) installBtnSection.addEventListener('click', triggerInstall);
  if (btnBannerInstall) btnBannerInstall.addEventListener('click', triggerInstall);

  if (btnBannerClose && mobileBanner) {
    btnBannerClose.addEventListener('click', () => {
      mobileBanner.style.display = 'none';
      sessionStorage.setItem('parkplus_dismissed_install', 'true');
    });
  }
}
