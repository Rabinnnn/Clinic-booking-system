// ---- State ----
let state = {
    doctors: [],
    selectedDoctor: null,
    selectedPatientName: '',
    selectedDate: null,
    availableSlots: [],
    patientAppointments: [],
    doctorAppointments: [],
    rescheduleAppointmentId: null,
    rescheduleDoctorId: null,
};

// ---- DOM refs ----
const $ = (id) => document.getElementById(id);
const doctorSelect = $('doctorSelect');
const patientNameInput = $('patientNameInput');
const dateInput = $('dateInput');
const checkBtn = $('checkAvailabilityBtn');
const slotsGrid = $('slotsGrid');
const slotsPlaceholder = $('slotsPlaceholder');
const slotMessage = $('slotMessage');

const appointmentsList = $('appointmentsList');
const appointmentsPlaceholder = $('appointmentsPlaceholder');

const doctorSelectDoctorView = $('doctorSelectDoctorView');
const loadDoctorAppointmentsBtn = $('loadDoctorAppointmentsBtn');
const doctorAppointmentsList = $('doctorAppointmentsList');
const doctorAppointmentsPlaceholder = $('doctorAppointmentsPlaceholder');

// Reschedule modal elements
const rescheduleDate = $('rescheduleDate');
const rescheduleCheckBtn = $('rescheduleCheckAvailabilityBtn');
const rescheduleSlotsGrid = $('rescheduleSlotsGrid');
const rescheduleSlotsPlaceholder = $('rescheduleSlotsPlaceholder');
const rescheduleError = $('rescheduleError');

// ---- UTC time formatter (avoids browser-timezone shift on ISO strings) ----
function fmtUTC(isoString) {
    const d = new Date(isoString);
    const h = d.getUTCHours();
    const m = String(d.getUTCMinutes()).padStart(2, '0');
    const period = h >= 12 ? 'PM' : 'AM';
    const h12 = h % 12 || 12;
    return `${h12}:${m} ${period}`;
}

// ---- API helpers ----
const API_BASE = '/api';

async function fetchJSON(url, options = {}) {
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `Request failed with status ${res.status}`);
    }
    return res.json();
}

// ---- Load doctors (shared) ----
async function loadDoctors() {
    try {
        const data = await fetchJSON(`${API_BASE}/doctors`);
        state.doctors = data;
        const options = '<option value="">— Select —</option>' +
            data.map(d => `<option value="${d.id}">Dr. ${d.name}</option>`).join('');
        doctorSelect.innerHTML = options;
        doctorSelectDoctorView.innerHTML = options;
    } catch (e) {
        showToast('Failed to load doctors: ' + e.message, 'danger');
    }
}

// ---- Get or create patient by name ----
async function getOrCreatePatient(name) {
    if (!name.trim()) throw new Error('Patient name is required.');
    const allPatients = await fetchJSON(`${API_BASE}/patients`);
    const existing = allPatients.find(p => p.name.toLowerCase() === name.trim().toLowerCase());
    if (existing) return existing.id;

    const email = name.trim().toLowerCase().replace(/\s+/g, '.') + '@clinic.local';
    const newPatient = await fetchJSON(`${API_BASE}/patients`, {
        method: 'POST',
        body: JSON.stringify({ name: name.trim(), email: email, phone: '' }),
    });
    return newPatient.id;
}

// ---- Patient Tab: Check Availability ----
async function checkAvailability() {
    const doctorId = parseInt(doctorSelect.value);
    const patientName = patientNameInput.value.trim();
    const date = dateInput.value;

    if (!doctorId) {
        showToast('Please select a doctor.', 'warning');
        return;
    }
    if (!patientName) {
        showToast('Please enter the patient name.', 'warning');
        return;
    }
    if (!date) {
        showToast('Please select a date.', 'warning');
        return;
    }

    state.selectedDoctor = doctorId;
    state.selectedPatientName = patientName;
    state.selectedDate = date;

    slotsGrid.style.display = 'none';
    slotsPlaceholder.style.display = 'block';
    slotsPlaceholder.innerHTML = '<i class="fas fa-spinner fa-spin fa-2x d-block mb-2"></i> Loading slots...';
    slotMessage.innerHTML = '';

    try {
        const data = await fetchJSON(`${API_BASE}/doctors/${doctorId}/availability?date=${date}`);
        state.availableSlots = data.slots || [];
        renderSlots(state.availableSlots);
        await loadPatientAppointments(patientName);
    } catch (e) {
        showToast('Error loading slots: ' + e.message, 'danger');
        slotsPlaceholder.innerHTML = 'Could not load slots.';
    }
}

function renderSlots(slots) {
    slotsPlaceholder.style.display = 'none';
    slotsGrid.style.display = 'flex';

    if (slots.length === 0) {
        slotsGrid.innerHTML = '<div class="w-100 text-muted text-center py-3">No free slots on this date.</div>';
        return;
    }

    slotsGrid.innerHTML = slots.map(slot => {
        const label = fmtUTC(slot.start) + ' – ' + fmtUTC(slot.end);
        return `<button class="slot-tile" data-start="${slot.start}" data-end="${slot.end}">
                    ${label}
                </button>`;
    }).join('');

    slotsGrid.querySelectorAll('.slot-tile').forEach(btn => {
        btn.addEventListener('click', () => bookSlot(btn.dataset.start));
    });
}

// ---- Book a slot ----
async function bookSlot(startTime) {
    const doctorId = state.selectedDoctor;
    const patientName = state.selectedPatientName;

    if (!doctorId || !patientName) {
        showToast('Please select a doctor and enter a patient name.', 'warning');
        return;
    }

    const btn = slotsGrid.querySelector(`[data-start="${startTime}"]`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }

    try {
        const patientId = await getOrCreatePatient(patientName);
        await fetchJSON(`${API_BASE}/appointments`, {
            method: 'POST',
            body: JSON.stringify({
                doctor_id: doctorId,
                patient_id: patientId,
                start_time: startTime,
            }),
        });
        showToast('✅ Appointment booked successfully!', 'success');
        await checkAvailability();
    } catch (e) {
        showToast('❌ ' + e.message, 'danger');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = fmtUTC(startTime) + ' – ' + fmtUTC(new Date(new Date(startTime).getTime() + 30*60000).toISOString());
        }
    }
}

// ---- Patient Tab: Load patient's upcoming appointments ----
async function loadPatientAppointments(patientName) {
    if (!patientName.trim()) {
        appointmentsPlaceholder.style.display = 'block';
        appointmentsList.style.display = 'none';
        return;
    }

    try {
        const allPatients = await fetchJSON(`${API_BASE}/patients`);
        const patient = allPatients.find(p => p.name.toLowerCase() === patientName.trim().toLowerCase());
        if (!patient) {
            appointmentsPlaceholder.style.display = 'block';
            appointmentsPlaceholder.innerHTML = 'No appointments yet for this patient.';
            appointmentsList.style.display = 'none';
            return;
        }
        const data = await fetchJSON(`${API_BASE}/patients/${patient.id}/appointments`);
        state.patientAppointments = data;
        renderPatientAppointments(data);
    } catch (e) {
        showToast('Error loading appointments: ' + e.message, 'danger');
    }
}

function renderPatientAppointments(appointments) {
    if (appointments.length === 0) {
        appointmentsPlaceholder.style.display = 'block';
        appointmentsPlaceholder.innerHTML = '<i class="fas fa-calendar-day fa-2x d-block mb-2"></i>No upcoming appointments.';
        appointmentsList.style.display = 'none';
        return;
    }

    appointmentsPlaceholder.style.display = 'none';
    appointmentsList.style.display = 'block';
    appointmentsList.innerHTML = appointments.map(app => appointmentCard(app, 'patient')).join('');
    attachAppointmentActions('patient');
}

// ---- Doctor Tab: Load doctor's appointments ----
async function loadDoctorAppointments() {
    const doctorId = parseInt(doctorSelectDoctorView.value);
    if (!doctorId) {
        // Silently return – the button handler shows the toast
        return;
    }

    try {
        const data = await fetchJSON(`${API_BASE}/doctors/${doctorId}/appointments`);
        state.doctorAppointments = data;
        renderDoctorAppointments(data);
    } catch (e) {
        showToast('Error loading doctor appointments: ' + e.message, 'danger');
    }
}

function renderDoctorAppointments(appointments) {
    if (appointments.length === 0) {
        doctorAppointmentsPlaceholder.style.display = 'block';
        doctorAppointmentsPlaceholder.innerHTML = '<i class="fas fa-calendar-day fa-2x d-block mb-2"></i>No upcoming appointments.';
        doctorAppointmentsList.style.display = 'none';
        return;
    }
    doctorAppointmentsPlaceholder.style.display = 'none';
    doctorAppointmentsList.style.display = 'block';
    doctorAppointmentsList.innerHTML = appointments.map(app => appointmentCard(app, 'doctor')).join('');
    attachAppointmentActions('doctor');
}

// ---- Appointment card helper ----
function appointmentCard(app, context) {
    const start = new Date(app.start_time);
    const end = new Date(app.end_time);
    const dateStr = start.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
    const timeStr = fmtUTC(app.start_time) + ' – ' + fmtUTC(app.end_time);
    const doctorName = state.doctors.find(d => d.id === app.doctor)?.name || `Doctor #${app.doctor}`;
    const patientName = app.patient_name || 'Patient';

    return `<div class="appointment-item d-flex justify-content-between align-items-center">
                <div>
                    <div class="time">${dateStr} · ${timeStr}</div>
                    <div class="doctor">
                        ${context === 'patient' ? `<i class="fas fa-user-md me-1"></i>Dr. ${doctorName}` :
                                                    `<i class="fas fa-user me-1"></i>${patientName}`}
                    </div>
                </div>
                <div class="actions d-flex gap-1">
                    <button class="btn btn-outline-primary btn-sm reschedule-btn" data-id="${app.id}" data-context="${context}">
                        <i class="fas fa-calendar-alt"></i> Reschedule
                    </button>
                    <button class="btn btn-outline-danger btn-sm cancel-btn" data-id="${app.id}" data-context="${context}">
                        <i class="fas fa-times"></i> Cancel
                    </button>
                </div>
            </div>`;
}

// ---- Attach cancel/reschedule listeners for a context ----
function attachAppointmentActions(context) {
    const list = context === 'patient' ? appointmentsList : doctorAppointmentsList;
    list.querySelectorAll('.cancel-btn').forEach(btn => {
        btn.addEventListener('click', () => promptCancel(btn.dataset.id, context));
    });
    list.querySelectorAll('.reschedule-btn').forEach(btn => {
        btn.addEventListener('click', () => openRescheduleModal(btn.dataset.id, context));
    });
}

// ---- Cancel ----
async function promptCancel(appointmentId, context) {
    const reason = prompt('Please provide a cancellation reason:');
    if (reason === null) return;
    if (reason.trim() === '') {
        showToast('Cancellation reason is required.', 'warning');
        return;
    }

    try {
        await fetchJSON(`${API_BASE}/appointments/${appointmentId}/cancel`, {
            method: 'PATCH',
            body: JSON.stringify({ reason: reason.trim() }),
        });
        showToast('✅ Appointment cancelled.', 'success');
        if (context === 'patient') {
            await checkAvailability();
        } else {
            await loadDoctorAppointments();
        }
    } catch (e) {
        showToast('❌ ' + e.message, 'danger');
    }
}

// ---- Reschedule Modal ----
let rescheduleModal = null;
const rescheduleModalEl = document.getElementById('rescheduleModal');

function openRescheduleModal(appointmentId, context) {
    let app;
    if (context === 'patient') {
        app = state.patientAppointments.find(a => a.id == appointmentId);
    } else {
        app = state.doctorAppointments.find(a => a.id == appointmentId);
    }
    if (!app) {
        showToast('Appointment not found.', 'danger');
        return;
    }

    state.rescheduleAppointmentId = appointmentId;
    state.rescheduleDoctorId = app.doctor;

    const patientName = app.patient_name || 'Patient';
    const doctor = state.doctors.find(d => d.id === app.doctor);
    document.getElementById('reschedulePatientName').textContent = patientName;
    document.getElementById('rescheduleDoctorName').textContent = doctor ? `Dr. ${doctor.name}` : 'Doctor';

    const today = new Date().toISOString().split('T')[0];
    rescheduleDate.value = '';
    rescheduleDate.min = today;
    rescheduleSlotsGrid.style.display = 'none';
    rescheduleSlotsPlaceholder.style.display = 'block';
    rescheduleSlotsPlaceholder.innerHTML = 'Pick a date and click "Check Availability"';
    rescheduleError.classList.add('d-none');

    if (!rescheduleModal) {
        rescheduleModal = new bootstrap.Modal(rescheduleModalEl);
    }
    rescheduleModal.show();
}

// ---- Render reschedule slots ----
function renderRescheduleSlots(slots) {
    rescheduleSlotsPlaceholder.style.display = 'none';
    rescheduleSlotsGrid.style.display = 'flex';

    if (slots.length === 0) {
        rescheduleSlotsGrid.innerHTML = '<div class="w-100 text-muted text-center py-3">No free slots on this date.</div>';
        return;
    }

    rescheduleSlotsGrid.innerHTML = slots.map(slot => {
        const label = fmtUTC(slot.start) + ' – ' + fmtUTC(slot.end);
        return `<button class="slot-tile" data-start="${slot.start}">
                    ${label}
                </button>`;
    }).join('');

    rescheduleSlotsGrid.querySelectorAll('.slot-tile').forEach(btn => {
        btn.addEventListener('click', function() {
            confirmReschedule(this.dataset.start);
        });
    });
}

// ---- Confirm reschedule ----
async function confirmReschedule(newStartTime) {
    if (!state.rescheduleAppointmentId) {
        showToast('Appointment ID missing.', 'danger');
        return;
    }

    const btn = rescheduleSlotsGrid.querySelector(`[data-start="${newStartTime}"]`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }

    try {
        await fetchJSON(`${API_BASE}/appointments/${state.rescheduleAppointmentId}/reschedule`, {
            method: 'PATCH',
            body: JSON.stringify({ new_start_time: newStartTime }),
        });
        showToast('✅ Appointment rescheduled!', 'success');
        if (rescheduleModal) rescheduleModal.hide();

        // Refresh patient view
        await checkAvailability();

        // Only refresh doctor view if the doctor tab is active
        const doctorPane = document.getElementById('doctor-pane');
        if (doctorPane.classList.contains('active')) {
            await loadDoctorAppointments();
        }
    } catch (e) {
        showToast('❌ ' + e.message, 'danger');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = fmtUTC(startTime) + ' – ' + fmtUTC(new Date(new Date(startTime).getTime() + 30*60000).toISOString());
        }
    }
}

// ---- Toast notifications ----
function showToast(message, type = 'info') {
    slotMessage.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show mb-0" role="alert">
                                ${message}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>`;
    setTimeout(() => {
        const alert = slotMessage.querySelector('.alert');
        if (alert) alert.remove();
    }, 5000);
}

// ---- Event listeners ----
checkBtn.addEventListener('click', checkAvailability);
dateInput.addEventListener('change', () => {
    if (state.selectedDoctor && state.selectedPatientName) {
        checkAvailability();
    }
});
patientNameInput.addEventListener('change', () => {});

loadDoctorAppointmentsBtn.addEventListener('click', function() {
    const doctorId = parseInt(doctorSelectDoctorView.value);
    if (!doctorId) {
        showToast('Please select a doctor.', 'warning');
        return;
    }
    loadDoctorAppointments();
});

// ---- Reschedule check availability ----
rescheduleCheckBtn.addEventListener('click', async function() {
    const date = rescheduleDate.value;
    if (!date) {
        rescheduleError.textContent = 'Please select a date.';
        rescheduleError.classList.remove('d-none');
        return;
    }

    const doctorId = state.rescheduleDoctorId;
    if (!doctorId) {
        rescheduleError.textContent = 'Doctor not found.';
        rescheduleError.classList.remove('d-none');
        return;
    }

    rescheduleSlotsPlaceholder.style.display = 'block';
    rescheduleSlotsPlaceholder.innerHTML = '<i class="fas fa-spinner fa-spin fa-2x d-block mb-2"></i> Loading slots...';
    rescheduleSlotsGrid.style.display = 'none';
    rescheduleError.classList.add('d-none');

    try {
        const data = await fetchJSON(`${API_BASE}/doctors/${doctorId}/availability?date=${date}`);
        const slots = data.slots || [];
        renderRescheduleSlots(slots);
    } catch (e) {
        rescheduleError.textContent = '❌ ' + e.message;
        rescheduleError.classList.remove('d-none');
    }
});

// ---- Init ----
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
    loadDoctors();

    rescheduleModalEl.addEventListener('hidden.bs.modal', function() {
        state.rescheduleAppointmentId = null;
        state.rescheduleDoctorId = null;
        rescheduleError.classList.add('d-none');
        rescheduleSlotsPlaceholder.style.display = 'block';
        rescheduleSlotsPlaceholder.innerHTML = 'Pick a date and click "Check Availability"';
        rescheduleSlotsGrid.style.display = 'none';
    });

    // ---- Doctor Tab Authentication with Modal ----
    const doctorTab = document.getElementById('doctor-tab');
    const authModalEl = document.getElementById('authModal');
    const authModal = new bootstrap.Modal(authModalEl, { backdrop: 'static' });
    const authInput = document.getElementById('authRegNumber');
    const authError = document.getElementById('authError');
    const authSubmit = document.getElementById('authSubmitBtn');
    const DOCTOR_REG_NUMBER = 'doc15/2026';
    let isDoctorAuthenticated = false;

    doctorTab.addEventListener('show.bs.tab', function(e) {
        if (!isDoctorAuthenticated) {
            e.preventDefault();
            authInput.value = '';
            authError.classList.add('d-none');
            authModal.show();
        }
    });

    authSubmit.addEventListener('click', function() {
        const entered = authInput.value.trim();
        if (entered === DOCTOR_REG_NUMBER) {
            isDoctorAuthenticated = true;
            authModal.hide();
            const tab = new bootstrap.Tab(doctorTab);
            tab.show();
            setTimeout(() => {
                if (doctorSelectDoctorView.value) {
                    loadDoctorAppointments();
                }
            }, 200);
        } else {
            authError.classList.remove('d-none');
            authInput.value = '';
            authInput.focus();
        }
    });

    authInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            authSubmit.click();
        }
    });

    authModalEl.addEventListener('hidden.bs.modal', function() {
        authError.classList.add('d-none');
        authInput.value = '';
    });
});