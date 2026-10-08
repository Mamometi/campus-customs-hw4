import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signup } from "../api";
import { useAuth } from "../auth";

export default function Signup() {
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "", confirm: "" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const update = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (form.password !== form.confirm) {
      setError("Passwords don't match");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { confirm: _confirm, ...data } = form;
      setSession(await signup(data));
      navigate("/products");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth">
      <form className="auth__card" onSubmit={handleSubmit}>
        <h1>Create your account</h1>
        <p className="auth__sub">Save your details and get personalized help from our assistant.</p>

        <div className="auth__row">
          <label>
            First name
            <input value={form.first_name} onChange={update("first_name")} required autoComplete="given-name" />
          </label>
          <label>
            Last name
            <input value={form.last_name} onChange={update("last_name")} required autoComplete="family-name" />
          </label>
        </div>
        <label>
          Email
          <input type="email" value={form.email} onChange={update("email")} required autoComplete="email" />
        </label>
        <label>
          Password
          <input
            type="password"
            value={form.password}
            onChange={update("password")}
            required
            minLength={8}
            autoComplete="new-password"
          />
          <small>At least 8 characters.</small>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            value={form.confirm}
            onChange={update("confirm")}
            required
            autoComplete="new-password"
          />
        </label>

        {error && <div className="notice notice--error">{error}</div>}

        <button className="btn btn--primary btn--block" disabled={loading}>
          {loading ? "Creating account…" : "Create account"}
        </button>
        <p className="auth__switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
