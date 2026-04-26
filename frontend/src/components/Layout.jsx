import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const { isLoggedIn, username, can, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="brand">
          <NavLink to="/" aria-label="Lolo Tours home">
            <img src="/logo.svg" alt="Lolo Tours" className="brand-logo" />
          </NavLink>
        </div>
        <nav className="primary-nav">
          <NavLink to="/" end>
            Home
          </NavLink>
          <NavLink to="/schedule">Schedule</NavLink>
          <NavLink to="/booking-lookup">My booking</NavLink>
          <NavLink to="/contact">Contact</NavLink>
          {can("tour-template:edit") && (
            <NavLink to="/admin/tours">Tour Builder</NavLink>
          )}
          {can("tour-slot:view") && (
            <NavLink to="/admin/tour-slots">Tour Slots</NavLink>
          )}
        </nav>
        <div className="auth-area">
          {isLoggedIn ? (
            <>
              <span className="auth-user">{username}</span>
              <button type="button" className="auth-btn" onClick={handleLogout}>
                Log out
              </button>
            </>
          ) : (
            <NavLink to="/login" className="auth-btn">
              Sign in
            </NavLink>
          )}
        </div>
      </header>
      <main className="site-main">
        <Outlet />
      </main>
      <footer className="site-footer">
        &copy; {new Date().getFullYear()} Lolo Tours
      </footer>
    </div>
  );
}
