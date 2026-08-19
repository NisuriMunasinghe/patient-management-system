import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000/api";

async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail?.message ||
        data.detail?.[0]?.msg ||
        "The request could not be completed."
    );
  }

  return data;
}

function formatDate(value) {
  return new Date(value).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function App() {
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [credentials, setCredentials] = useState({
    email: "",
    password: "",
  });
  const [doctors, setDoctors] = useState([]);
  const [specialty, setSpecialty] = useState("");
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [slots, setSlots] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [schedule, setSchedule] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) return;

    apiRequest("/auth/me")
      .then(setUser)
      .catch(() => localStorage.removeItem("token"));
  }, []);

  useEffect(() => {
    if (user?.role === "patient") {
      loadDoctors();
      loadAppointments();
    }

    if (user?.role === "doctor") {
      loadSchedule();
    }
  }, [user]);

  function clearNotices() {
    setError("");
    setMessage("");
  }

  async function handleAuthentication(event) {
    event.preventDefault();
    clearNotices();
    setLoading(true);

    try {
      if (authMode === "register") {
        await apiRequest("/auth/register", {
          method: "POST",
          body: JSON.stringify(credentials),
        });
      }

      const result = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials),
      });

      localStorage.setItem("token", result.access_token);
      setUser(result.user);
      setCredentials({ email: "", password: "" });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadDoctors(searchValue = "") {
    clearNotices();

    try {
      const query = searchValue
        ? `?specialty=${encodeURIComponent(searchValue)}`
        : "";
      setDoctors(await apiRequest(`/doctors${query}`));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function loadSlots(doctor) {
    clearNotices();
    setSelectedDoctor(doctor);

    try {
      setSlots(await apiRequest(`/doctors/${doctor.id}/slots`));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function loadAppointments() {
    try {
      setAppointments(await apiRequest("/appointments/me"));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function loadSchedule() {
    try {
      setSchedule(await apiRequest("/doctors/me/schedule?days=7"));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function bookSlot(slotId) {
    clearNotices();

    try {
      await apiRequest("/appointments", {
        method: "POST",
        body: JSON.stringify({ slot_id: slotId }),
      });

      setMessage("Appointment booked successfully.");
      await Promise.all([
        loadSlots(selectedDoctor),
        loadAppointments(),
      ]);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function cancelAppointment(appointmentId) {
    clearNotices();

    try {
      await apiRequest(`/appointments/${appointmentId}`, {
        method: "DELETE",
      });

      setMessage("Appointment cancelled.");
      await loadAppointments();

      if (selectedDoctor) {
        await loadSlots(selectedDoctor);
      }
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function logout() {
    localStorage.removeItem("token");
    setUser(null);
    setDoctors([]);
    setSlots([]);
    setAppointments([]);
    setSchedule([]);
    setSelectedDoctor(null);
    clearNotices();
  }

  if (!user) {
    return (
      <main className="auth-page">
        <section className="auth-card">
          <p className="eyebrow">CLINICFLOW</p>
          <h1>Patient Management System</h1>
          <p className="muted">
            Book and manage medical appointments securely.
          </p>

          <form onSubmit={handleAuthentication}>
            <label>
              Email address
              <input
                type="email"
                required
                value={credentials.email}
                onChange={(event) =>
                  setCredentials({
                    ...credentials,
                    email: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Password
              <input
                type="password"
                required
                minLength="8"
                value={credentials.password}
                onChange={(event) =>
                  setCredentials({
                    ...credentials,
                    password: event.target.value,
                  })
                }
              />
            </label>

            {error && <div className="notice error">{error}</div>}

            <button disabled={loading} type="submit">
              {loading
                ? "Please wait..."
                : authMode === "login"
                  ? "Log in"
                  : "Create patient account"}
            </button>
          </form>

          <button
            className="link-button"
            onClick={() => {
              clearNotices();
              setAuthMode(
                authMode === "login" ? "register" : "login"
              );
            }}
          >
            {authMode === "login"
              ? "New patient? Register"
              : "Already registered? Log in"}
          </button>

          <div className="demo-credentials">
            <strong>Doctor demo</strong>
            <span>maya.fernando@clinicflow.com</span>
            <span>Password: Doctor123!</span>
          </div>
        </section>
      </main>
    );
  }

  return (
    <>
      <header>
        <div>
          <p className="eyebrow">CLINICFLOW</p>
          <h2>
            {user.role === "patient"
              ? "Patient Dashboard"
              : "Doctor Schedule"}
          </h2>
        </div>

        <div className="header-user">
          <span>{user.email}</span>
          <button className="secondary" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      <main className="dashboard">
        {error && <div className="notice error">{error}</div>}
        {message && <div className="notice success">{message}</div>}

        {user.role === "patient" ? (
          <>
            <section className="panel">
              <h3>Find a doctor</h3>

              <form
                className="search"
                onSubmit={(event) => {
                  event.preventDefault();
                  loadDoctors(specialty);
                }}
              >
                <input
                  placeholder="Search by specialty"
                  value={specialty}
                  onChange={(event) =>
                    setSpecialty(event.target.value)
                  }
                />
                <button type="submit">Search</button>
              </form>

              <div className="card-grid">
                {doctors.map((doctor) => (
                  <article className="doctor-card" key={doctor.id}>
                    <h4>{doctor.full_name}</h4>
                    <p>{doctor.specialty}</p>
                    <button onClick={() => loadSlots(doctor)}>
                      View available slots
                    </button>
                  </article>
                ))}
              </div>
            </section>

            {selectedDoctor && (
              <section className="panel">
                <h3>Available times — {selectedDoctor.full_name}</h3>

                {slots.length === 0 ? (
                  <p className="muted">No available slots.</p>
                ) : (
                  <div className="slot-list">
                    {slots.map((slot) => (
                      <div className="list-row" key={slot.id}>
                        <span>{formatDate(slot.starts_at)}</span>
                        <button onClick={() => bookSlot(slot.id)}>
                          Book
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}

            <section className="panel">
              <h3>Upcoming appointments</h3>

              {appointments.length === 0 ? (
                <p className="muted">
                  You have no upcoming appointments.
                </p>
              ) : (
                <div className="slot-list">
                  {appointments.map((appointment) => (
                    <div className="list-row" key={appointment.id}>
                      <div>
                        <strong>{appointment.doctor_name}</strong>
                        <span>
                          {appointment.specialty} ·{" "}
                          {formatDate(appointment.starts_at)}
                        </span>
                      </div>
                      <button
                        className="danger"
                        onClick={() =>
                          cancelAppointment(appointment.id)
                        }
                      >
                        Cancel
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        ) : (
          <section className="panel">
            <h3>Your next seven days</h3>

            {schedule.length === 0 ? (
              <p className="muted">
                No appointments are currently scheduled.
              </p>
            ) : (
              <div className="slot-list">
                {schedule.map((item) => (
                  <div className="list-row" key={item.appointment_id}>
                    <div>
                      <strong>{item.patient_email}</strong>
                      <span>{formatDate(item.starts_at)}</span>
                    </div>
                    <span className="badge">{item.status}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>
    </>
  );
}

export default App;