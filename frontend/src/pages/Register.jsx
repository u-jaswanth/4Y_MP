import { useState } from "react";
import { registerPatient } from "../services/api";
import { useNavigate } from "react-router-dom";
import AuthBrand from "../components/AuthBrand";

function Register() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: "",
    age: "",
    gender: "",
    mobile: "",
    email: "",
    aadhaar_number: "",
    password: "",
    confirm_password: "",
    aadhaar_consent: false,
    aadhaar_photo: null,
  });

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [healthId, setHealthId] = useState("");

  function handleChange(event) {
    const { name, value, type, checked } = event.target;

    setForm({
      ...form,
      [name]: type === "checkbox" ? checked : value,
    });
  }

  function handleFileChange(event) {
    setForm({
      ...form,
      aadhaar_photo: event.target.files[0],
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setMessage("");
    setError("");
    setHealthId("");

    if (form.password !== form.confirm_password) {
      setError("Passwords do not match");
      return;
    }

    if (!form.aadhaar_consent) {
      setError("Please provide Aadhaar consent");
      return;
    }

    if (!form.aadhaar_photo) {
      setError("Please upload Aadhaar photo");
      return;
    }

    try {
      const patientData = {
        full_name: form.full_name,
        age: Number(form.age),
        gender: form.gender,
        mobile: form.mobile,
        email: form.email,
        password: form.password,
        aadhaar_number: form.aadhaar_number,
        aadhaar_consent: form.aadhaar_consent,
        aadhaar_photo: form.aadhaar_photo,
      };

      const result = await registerPatient(patientData);

      setMessage(result.message);
      setHealthId(result.health_id);

      setForm({
        full_name: "",
        age: "",
        gender: "",
        mobile: "",
        email: "",
        aadhaar_number: "",
        password: "",
        confirm_password: "",
        aadhaar_consent: false,
        aadhaar_photo: null,
      });

    } catch (error) {
      setError(error.message);
    }
  }

  return (
    <div className="auth-page">

      <AuthBrand
        title="Create your health record in two minutes."
        intro="Register once, then keep every report and its explanation together, and share them with a doctor only when you choose to."
        points={[
          { icon: "file", text: "A personal Health ID with a QR code" },
          { icon: "reports", text: "Secure storage for every report" },
          { icon: "spark", text: "AI that explains your results" },
        ]}
      />


      <div className="auth-container">

        <div className="auth-card">

          <h2>Create account</h2>

          <p className="auth-subtitle">
            Create your MediConnect patient profile.
          </p>


          {error && (
            <div className="error-message">
              {error}
            </div>
          )}


          <form onSubmit={handleSubmit}>

            <div className="form-group">
              <label htmlFor="reg-full_name">Full Name</label>

              <input
                className="form-input"
                type="text"
                id="reg-full_name" name="full_name"
                placeholder="Your full name"
                value={form.full_name}
                onChange={handleChange}
                required
              />
            </div>


            <div className="form-row">

              <div className="form-group">
                <label htmlFor="reg-age">Age</label>

                <input
                  className="form-input"
                  type="number"
                  id="reg-age" name="age"
                  placeholder="Age"
                  value={form.age}
                  onChange={handleChange}
                  required
                />
              </div>


              <div className="form-group">
                <label htmlFor="reg-gender">Gender</label>

                <select
                  className="form-select"
                  id="reg-gender" name="gender"
                  value={form.gender}
                  onChange={handleChange}
                  required
                >
                  <option value="">
                    Select
                  </option>

                  <option value="Male">
                    Male
                  </option>

                  <option value="Female">
                    Female
                  </option>

                  <option value="Other">
                    Other
                  </option>

                </select>

              </div>

            </div>


            <div className="form-row">

              <div className="form-group">
                <label htmlFor="reg-mobile">Mobile</label>

                <input
                  className="form-input"
                  type="tel"
                  id="reg-mobile" name="mobile"
                  placeholder="Mobile number"
                  value={form.mobile}
                  onChange={handleChange}
                  required
                />
              </div>


              <div className="form-group">
                <label htmlFor="reg-email">Email</label>

                <input
                  className="form-input"
                  type="email"
                  id="reg-email" name="email"
                  placeholder="Email address"
                  value={form.email}
                  onChange={handleChange}
                  required
                />
              </div>

            </div>


            <div className="form-group">
              <label htmlFor="reg-aadhaar_number">Aadhaar Number</label>

              <input
                className="form-input"
                type="text"
                id="reg-aadhaar_number" name="aadhaar_number"
                placeholder="Aadhaar number"
                value={form.aadhaar_number}
                onChange={handleChange}
                required
              />
            </div>


            <div className="form-group">

              <label htmlFor="reg-aadhaar_photo">
                Aadhaar Photo
              </label>

              <input
                className="file-input"
                type="file"
                id="reg-aadhaar_photo" name="aadhaar_photo"
                accept="image/*"
                onChange={handleFileChange}
                required
              />

            </div>


            <div className="form-row">

              <div className="form-group">

                <label htmlFor="reg-password">Password</label>

                <input
                  className="form-input"
                  type="password"
                  id="reg-password" name="password"
                  placeholder="Password"
                  value={form.password}
                  onChange={handleChange}
                  required
                />

              </div>


              <div className="form-group">

                <label htmlFor="reg-confirm_password">Confirm Password</label>

                <input
                  className="form-input"
                  type="password"
                  id="reg-confirm_password" name="confirm_password"
                  placeholder="Confirm password"
                  value={form.confirm_password}
                  onChange={handleChange}
                  required
                />

              </div>

            </div>


            <label className="checkbox-row">

              <input
                type="checkbox"
                name="aadhaar_consent"
                checked={form.aadhaar_consent}
                onChange={handleChange}
              />

              <span>
                I consent to Aadhaar verification for
                identity verification.
              </span>

            </label>


            <button
              className="primary-btn"
              type="submit"
            >
              Create Patient Account
            </button>

          </form>


          {message && (
            <div className="success-message">
              {message}
            </div>
          )}


          {healthId && (
            <div className="health-id-result">

              <div>
                Your Health ID
              </div>

              <div className="health-id">
                {healthId}
              </div>

              <button
                className="secondary-btn"
                style={{ marginTop: "15px" }}
                onClick={() => navigate("/login")}
              >
                Continue to Login
              </button>

            </div>
          )}


          <div className="auth-switch">

            Already have an account?

            <button
              onClick={() => navigate("/login")}
            >
              Sign in
            </button>

          </div>

        </div>

      </div>

    </div>
  );
}

export default Register;