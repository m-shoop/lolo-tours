import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function RequirePermission({ permission, children }) {
  const { isLoggedIn, can } = useAuth();
  const location = useLocation();

  if (!isLoggedIn) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (permission && !can(permission)) {
    return (
      <div style={{ padding: "2rem", maxWidth: 600 }}>
        <h2>Access denied</h2>
        <p>You don't have permission to view this page.</p>
      </div>
    );
  }
  return children;
}
