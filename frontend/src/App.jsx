import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout.jsx";
import ReauthModal from "./components/ReauthModal/ReauthModal.jsx";
import RequirePermission from "./components/RequirePermission.jsx";
import SessionExpiredBanner from "./components/SessionExpiredBanner/SessionExpiredBanner.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import BookingLookup from "./pages/BookingLookup.jsx";
import Cancelled from "./pages/Cancelled.jsx";
import Confirmation from "./pages/Confirmation.jsx";
import Contact from "./pages/Contact.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login/Login.jsx";
import Schedule from "./pages/Schedule/Schedule.jsx";
import TourBuilderEdit from "./pages/TourBuilder/TourBuilderEdit.jsx";
import TourBuilderList from "./pages/TourBuilder/TourBuilderList.jsx";
import TourSlotEdit from "./pages/TourSlots/TourSlotEdit.jsx";
import TourSlotsList from "./pages/TourSlots/TourSlotsList.jsx";

export default function App() {
  return (
    <AuthProvider>
      <SessionExpiredBanner />
      <ReauthModal />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/confirmation" element={<Confirmation />} />
          <Route path="/canceled" element={<Cancelled />} />
          <Route path="/booking-lookup" element={<BookingLookup />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/login" element={<Login />} />

          <Route
            path="/admin/tours"
            element={
              <RequirePermission permission="tour-template:edit">
                <TourBuilderList />
              </RequirePermission>
            }
          />
          <Route
            path="/admin/tours/new"
            element={
              <RequirePermission permission="tour-template:edit">
                <TourBuilderEdit mode="create" />
              </RequirePermission>
            }
          />
          <Route
            path="/admin/tours/:tourId"
            element={
              <RequirePermission permission="tour-template:edit">
                <TourBuilderEdit mode="edit" />
              </RequirePermission>
            }
          />

          <Route
            path="/admin/tour-slots"
            element={
              <RequirePermission permission="tour-slot:view">
                <TourSlotsList />
              </RequirePermission>
            }
          />
          <Route
            path="/admin/tour-slots/new"
            element={
              <RequirePermission permission="tour-slot:edit">
                <TourSlotEdit mode="create" />
              </RequirePermission>
            }
          />
          <Route
            path="/admin/tour-slots/:slotId"
            element={
              <RequirePermission permission="tour-slot:edit">
                <TourSlotEdit mode="edit" />
              </RequirePermission>
            }
          />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
