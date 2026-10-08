import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/products", label: "Products", end: false },
  { to: "/about", label: "About Us", end: true },
];

export default function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <>
    <div className="announce">
      <strong>Yale apparel since 1975</strong>
      <span>·</span>
      <em>Family-run on Broadway, New Haven</em>
      <span>·</span>
      <em>Every college, school &amp; team, XS–XXL</em>
    </div>
    <header className="nav">
      <div className="nav__inner">
        <Link to="/" className="nav__brand" onClick={close}>
          <span className="nav__logo" aria-hidden>CC</span>
          <span className="nav__name">
            Campus Customs
            <small>New Haven · Est. 1975</small>
          </span>
        </Link>

        <button
          className="nav__toggle"
          aria-label="Toggle menu"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          ☰
        </button>

        <nav className={`nav__links ${open ? "nav__links--open" : ""}`}>
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} onClick={close}>
              {l.label}
            </NavLink>
          ))}
          <span className="nav__divider" aria-hidden />
          {user ? (
            <>
              <span className="nav__greeting">Hi, {user.first_name}</span>
              <button
                className="nav__button nav__button--ghost"
                onClick={() => {
                  logout();
                  close();
                  navigate("/");
                }}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" onClick={close}>
                Login
              </NavLink>
              <NavLink to="/signup" className="nav__button" onClick={close}>
                Create Account
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
    </>
  );
}
