let currentStep = 'scan';
let currentAttemptId = null;
let currentLocation = null;
let currentAuthOptions = null;
let qrScanner = null;
let qrCameraStream = null;
let qrScanTimer = null;
let qrDetectionInProgress = false;

function showStep(step) {
  document.getElementById('scan-step').classList.add('hidden');
  document.getElementById('location-step').classList.add('hidden');
  document.getElementById('passkey-step').classList.add('hidden');
  document.getElementById('success-step').classList.add('hidden');
  document.getElementById('error-step').classList.add('hidden');

  document.getElementById(`${step}-step`).classList.remove('hidden');
  currentStep = step;
}

function showToast(message) {
  const toast = document.getElementById('toast');
  const toastMessage = document.getElementById('toast-message');
  toastMessage.textContent = message;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 3000);
}

function setButtonLoading(buttonId, loading) {
  const button = document.getElementById(buttonId);
  button.disabled = loading;
  button.textContent = loading ? 'Processing...' : button.dataset.originalText || button.textContent;
}

async function beginCheckIn(sessionId, qrToken) {
  try {
    const response = await fetch('/api/v1/checkins/begin', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({
        session_id: sessionId,
        qr_token: qrToken,
        device_hint: generateDeviceHint(),
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error?.message || 'Failed to begin check-in');
    }

    currentAttemptId = data.attempt_id;
    currentAuthOptions = data;
    showStep('location');
  } catch (error) {
    showError(error.message);
  }
}

async function getLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation is not supported by your browser'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy_m: position.coords.accuracy,
          timestamp: Date.now() / 1000,
        });
      },
      (error) => {
        const message = error.code === error.PERMISSION_DENIED
          ? 'Allow location access in your browser settings, then try again.'
          : error.code === error.POSITION_UNAVAILABLE
            ? 'Your device could not determine a location. Move near a window and retry.'
            : 'Location request timed out. Please try again.';
        reject(new Error(message));
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  });
}

async function completeCheckIn(assertion) {
  try {
    const response = await fetch('/api/v1/checkins/complete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({
        attempt_id: currentAttemptId,
        assertion: assertion,
        location: currentLocation,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      if (data.error?.code === 'OUTSIDE_CLASSROOM') {
        currentLocation = null;
        document.getElementById('location-error').textContent = data.error.message;
        document.getElementById('location-error').classList.remove('hidden');
        showStep('location');
        return;
      }
      throw new Error(data.error?.message || 'Failed to complete check-in');
    }

    if (data.status === 'FLAGGED') {
      showError('Your check-in was flagged for review. Please see your teacher.');
    } else {
      showStep('success');
    }
  } catch (error) {
    showError(error.message);
  }
}

function showError(message) {
  document.getElementById('error-message').textContent = message;
  showStep('error');
}

function generateDeviceHint() {
  let hint = '';
  const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) {
    hint += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return hint;
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

function getCsrfToken() {
  return document.querySelector('#csrf-token-form [name="csrfmiddlewaretoken"]')?.value || getCookie('csrftoken');
}

function decodeBase64Url(value) {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - value.length % 4) % 4);
  return Uint8Array.from(atob(base64), character => character.charCodeAt(0));
}

function encodeBuffer(value) {
  return btoa(String.fromCharCode(...new Uint8Array(value)));
}

function distanceMeters(first, second) {
  const radians = degrees => degrees * Math.PI / 180;
  const latitudeDelta = radians(second.lat - first.lat);
  const longitudeDelta = radians(second.lng - first.lng);
  const arc = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(radians(first.lat)) * Math.cos(radians(second.lat))
    * Math.sin(longitudeDelta / 2) ** 2;
  return 6371000 * 2 * Math.asin(Math.sqrt(arc));
}

async function loadQrLibrary() {
  if (window.Html5Qrcode) return;
  await new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js';
    const timeout = setTimeout(() => reject(new Error('QR scanner took too long to load. Try again or paste the QR link.')), 12000);
    script.onload = () => {
      clearTimeout(timeout);
      if (window.Html5Qrcode) resolve();
      else reject(new Error('QR scanner did not initialize. Try again or paste the QR link.'));
    };
    script.onerror = () => {
      clearTimeout(timeout);
      reject(new Error('Could not load the QR scanner. Check your connection or paste the QR link.'));
    };
    document.head.appendChild(script);
  });
}

async function handleScannedQr(decodedText) {
  document.getElementById('qr-input').value = decodedText;
  document.getElementById('camera-status').textContent = 'QR code found. Checking it now.';
  await stopCameraScan();
  document.getElementById('scan-btn').click();
}

async function startCameraScan() {
  const cameraError = document.getElementById('camera-error');
  const cameraStatus = document.getElementById('camera-status');
  const startButton = document.getElementById('camera-start-btn');
  cameraError.classList.add('hidden');
  startButton.disabled = true;
  startButton.textContent = 'Starting camera...';
  cameraStatus.textContent = 'Requesting camera permission...';
  try {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      throw new Error('Camera scanning requires HTTPS or localhost. Open this page using the secure site link.');
    }

    qrCameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    });

    if ('BarcodeDetector' in window) {
      const video = document.getElementById('qr-camera');
      const detector = new BarcodeDetector({ formats: ['qr_code'] });
      video.srcObject = qrCameraStream;
      video.hidden = false;
      await video.play();
      startButton.classList.add('hidden');
      document.getElementById('camera-stop-btn').classList.remove('hidden');
      cameraStatus.textContent = 'Camera is on. Point it at the teacher’s QR code.';
      qrScanTimer = setInterval(async () => {
        if (qrDetectionInProgress || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;
        qrDetectionInProgress = true;
        try {
          const codes = await detector.detect(video);
          if (codes.length) await handleScannedQr(codes[0].rawValue);
        } catch {
          cameraStatus.textContent = 'Keep the QR code in view and hold your phone steady.';
        } finally {
          qrDetectionInProgress = false;
        }
      }, 250);
      return;
    }

    qrCameraStream.getTracks().forEach(track => track.stop());
    qrCameraStream = null;
    cameraStatus.textContent = 'Loading the compatible QR scanner...';
    await loadQrLibrary();
    qrScanner = new Html5Qrcode('qr-reader');
    startButton.classList.add('hidden');
    document.getElementById('camera-stop-btn').classList.remove('hidden');
    cameraStatus.textContent = 'Camera is on. Point it at the teacher’s QR code.';
    await qrScanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 240, height: 240 } },
      handleScannedQr,
      () => {}
    );
  } catch (error) {
    if (qrCameraStream) {
      qrCameraStream.getTracks().forEach(track => track.stop());
      qrCameraStream = null;
    }
    const message = error.name === 'NotAllowedError'
      ? 'Camera permission was blocked. Allow camera access in browser settings, then try again.'
      : error.name === 'NotFoundError'
        ? 'No camera was found on this device.'
        : error.name === 'NotReadableError'
          ? 'The camera is being used by another app. Close it and try again.'
          : error.message || 'Camera could not start. Check browser camera permission.';
    cameraError.textContent = message;
    cameraError.classList.remove('hidden');
    cameraStatus.textContent = 'Camera did not start.';
    startButton.classList.remove('hidden');
    document.getElementById('camera-stop-btn').classList.add('hidden');
  } finally {
    startButton.disabled = false;
    startButton.textContent = 'Scan with camera';
  }
}

async function stopCameraScan() {
  if (qrScanTimer) {
    clearInterval(qrScanTimer);
    qrScanTimer = null;
  }
  if (qrCameraStream) {
    qrCameraStream.getTracks().forEach(track => track.stop());
    qrCameraStream = null;
  }
  const video = document.getElementById('qr-camera');
  video.pause();
  video.srcObject = null;
  video.hidden = true;
  if (qrScanner?.isScanning) {
    await qrScanner.stop();
    qrScanner.clear();
  }
  qrScanner = null;
  const startButton = document.getElementById('camera-start-btn');
  startButton.textContent = 'Scan with camera';
  startButton.classList.remove('hidden');
  document.getElementById('camera-stop-btn').classList.add('hidden');
  document.getElementById('camera-status').textContent = 'Camera stopped.';
}

function parseQRUrl(url) {
  try {
    const urlObj = new URL(url);
    const pathParts = urlObj.pathname.split('/').filter(Boolean);
    const sessionId = pathParts[0] === 'c' ? pathParts[1] : null;
    const token = urlObj.searchParams.get('t');
    return { sessionId, token };
  } catch {
    return null;
  }
}

export const checkin = {
  init() {
    const scanBtn = document.getElementById('scan-btn');
    const locationBtn = document.getElementById('location-btn');
    const passkeyBtn = document.getElementById('passkey-btn');
    const cameraStartBtn = document.getElementById('camera-start-btn');
    const cameraStopBtn = document.getElementById('camera-stop-btn');
    const retryBtn = document.getElementById('retry-btn');
    const qrInput = document.getElementById('qr-input');

    scanBtn.dataset.originalText = scanBtn.textContent;
    locationBtn.dataset.originalText = locationBtn.textContent;
    passkeyBtn.dataset.originalText = passkeyBtn.textContent;
    cameraStartBtn.addEventListener('click', startCameraScan);
    cameraStopBtn.addEventListener('click', stopCameraScan);

    const initialQrValue = new URLSearchParams(window.location.search).get('t');
    if (initialQrValue) {
      qrInput.value = `${window.location.origin}${window.location.pathname}?t=${initialQrValue}`;
      setTimeout(() => scanBtn.click(), 0);
    }

    scanBtn.addEventListener('click', async () => {
      const qrValue = qrInput.value.trim();
      if (!qrValue) {
        showToast('Please enter or scan a QR code');
        return;
      }

      const parsed = parseQRUrl(qrValue);
      if (!parsed || !parsed.sessionId || !parsed.token) {
        showToast('Invalid QR code format');
        return;
      }

      setButtonLoading('scan-btn', true);
      await beginCheckIn(parsed.sessionId, parsed.token);
      setButtonLoading('scan-btn', false);
    });

    locationBtn.addEventListener('click', async () => {
      setButtonLoading('location-btn', true);
      try {
        currentLocation = await getLocation();
        const classroom = currentAuthOptions?.classroom;
        if (classroom && distanceMeters(currentLocation, classroom) > classroom.radius_m) {
          currentLocation = null;
          throw new Error('You are outside the classroom check-in area. Go to class and share your location again.');
        }
        document.getElementById('location-error').classList.add('hidden');
        document.getElementById('location-status').textContent = `Location received (accuracy ±${Math.round(currentLocation.accuracy_m)} m). Confirm your passkey next.`;
        showStep('passkey');
      } catch (error) {
        document.getElementById('location-error').textContent = error.message;
        document.getElementById('location-error').classList.remove('hidden');
      }
      setButtonLoading('location-btn', false);
    });

    passkeyBtn.addEventListener('click', async () => {
      setButtonLoading('passkey-btn', true);
      try {
        if (!currentAuthOptions || !currentLocation) {
          throw new Error('Scan the class QR and share your location first.');
        }
        const credential = await navigator.credentials.get({
          publicKey: {
            challenge: decodeBase64Url(currentAuthOptions.challenge),
            rpId: currentAuthOptions.rp_id,
            timeout: currentAuthOptions.timeout,
            allowCredentials: currentAuthOptions.allow_credentials.map(id => ({
              type: 'public-key',
              id: decodeBase64Url(id),
            })),
            userVerification: 'preferred',
          },
        });
        const assertion = {
          credentialId: credential.id,
          response: {
            clientDataJSON: encodeBuffer(credential.response.clientDataJSON),
            authenticatorData: encodeBuffer(credential.response.authenticatorData),
            signature: encodeBuffer(credential.response.signature),
            userHandle: credential.response.userHandle
              ? encodeBuffer(credential.response.userHandle)
              : null,
          },
        };
        await completeCheckIn(assertion);
      } catch (error) {
        document.getElementById('passkey-error').textContent = error.message;
        document.getElementById('passkey-error').classList.remove('hidden');
      }
      setButtonLoading('passkey-btn', false);
    });

    retryBtn.addEventListener('click', () => {
      if (
        currentAttemptId
        && currentAuthOptions
        && Date.parse(currentAuthOptions.expires_at) > Date.now()
      ) {
        showStep(currentLocation ? 'passkey' : 'location');
        return;
      }
      currentAttemptId = null;
      currentLocation = null;
      currentAuthOptions = null;
      document.getElementById('location-error').classList.add('hidden');
      document.getElementById('passkey-error').classList.add('hidden');
      showStep('scan');
    });
  },
};
