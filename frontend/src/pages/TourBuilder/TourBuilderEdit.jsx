import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { runReport } from "../../api/reports";
import {
  createTour,
  deleteTourImage,
  getTour,
  listTourImages,
  updateTour,
  updateTourImage,
  uploadTourImage,
} from "../../api/tours";
import { useAuth } from "../../context/AuthContext";
import styles from "./TourBuilder.module.css";

const EMPTY = {
  name: "",
  description: "",
  price_per_person_dollars: "",
  duration_minutes: 60,
  max_capacity: 1,
  is_active: true,
};

export default function TourBuilderEdit({ mode }) {
  const { tourId } = useParams();
  const navigate = useNavigate();
  const { can } = useAuth();
  const canEditImages = can("tour-image:edit");

  const [form, setForm] = useState(EMPTY);
  const [images, setImages] = useState([]);
  // Snapshot of saved form values; null until first load completes. Used to
  // gate the Save button by whether anything has actually changed.
  const [original, setOriginal] = useState(null);
  const [loading, setLoading] = useState(mode === "edit");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const hasChanges = useMemo(() => {
    if (mode !== "edit" || !original) return true;
    return (
      String(form.name) !== String(original.name) ||
      String(form.description) !== String(original.description) ||
      String(form.price_per_person_dollars) !==
        String(original.price_per_person_dollars) ||
      String(form.duration_minutes) !== String(original.duration_minutes) ||
      String(form.max_capacity) !== String(original.max_capacity) ||
      Boolean(form.is_active) !== Boolean(original.is_active)
    );
  }, [mode, original, form]);

  useEffect(() => {
    if (mode !== "edit" || !tourId) return;
    let cancelled = false;
    (async () => {
      try {
        const row = await getTour(tourId);
        const loaded = {
          name: row.name,
          description: row.description ?? "",
          price_per_person_dollars: (row.price_per_person / 100).toFixed(2),
          duration_minutes: row.duration_minutes,
          max_capacity: row.max_capacity,
          is_active: row.is_active,
        };
        setForm(loaded);
        setOriginal(loaded);
        const imgs = await listTourImages(tourId);
        if (!cancelled) setImages(imgs);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, tourId]);

  function setField(name, value) {
    setForm((f) => ({ ...f, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setSaving(true);

    const dollars = parseFloat(form.price_per_person_dollars);
    if (Number.isNaN(dollars) || dollars < 0) {
      setError("Price must be a non-negative number");
      setSaving(false);
      return;
    }

    const payload = {
      name: form.name,
      description: form.description || null,
      price_per_person: Math.round(dollars * 100),
      duration_minutes: Number(form.duration_minutes),
      max_capacity: Number(form.max_capacity),
      is_active: form.is_active,
    };

    try {
      if (mode === "create") {
        const created = await createTour(payload);
        navigate(`/admin/tours/${created.id}`, { replace: true });
        setNotice("Tour created.");
      } else {
        await updateTour(tourId, payload);
        setOriginal({ ...form });
        setNotice("Saved.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className={styles.page}>Loading…</div>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>
          {mode === "create" ? "New tour template" : "Edit tour template"}
        </h1>
        <Link to="/admin/tours" className={styles.secondaryBtn}>
          ← Back
        </Link>
      </div>

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.formRow}>
          <label htmlFor="name">Name</label>
          <input
            id="name"
            className={styles.input}
            maxLength={50}
            required
            value={form.name}
            onChange={(e) => setField("name", e.target.value)}
          />
        </div>

        <div className={styles.formRow}>
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            className={styles.textarea}
            maxLength={500}
            value={form.description}
            onChange={(e) => setField("description", e.target.value)}
          />
        </div>

        <div className={styles.formRow}>
          <label htmlFor="price">Price per person (USD)</label>
          <input
            id="price"
            className={styles.input}
            type="number"
            step="0.01"
            min="0"
            required
            value={form.price_per_person_dollars}
            onChange={(e) =>
              setField("price_per_person_dollars", e.target.value)
            }
          />
        </div>

        <div className={styles.formRow}>
          <label htmlFor="duration">Duration (minutes)</label>
          <input
            id="duration"
            className={styles.input}
            type="number"
            min="1"
            required
            value={form.duration_minutes}
            onChange={(e) => setField("duration_minutes", e.target.value)}
          />
        </div>

        <div className={styles.formRow}>
          <label htmlFor="capacity">Max capacity</label>
          <input
            id="capacity"
            className={styles.input}
            type="number"
            min="1"
            required
            value={form.max_capacity}
            onChange={(e) => setField("max_capacity", e.target.value)}
          />
        </div>

        <div className={styles.formRow}>
          <label htmlFor="is_active">Active</label>
          <div className={styles.toggleRow}>
            <input
              id="is_active"
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setField("is_active", e.target.checked)}
            />
            <span style={{ color: form.is_active ? "inherit" : "var(--color-muted)" }}>
              Active
            </span>
          </div>
        </div>

        {error && <div className={styles.error}>{error}</div>}
        {notice && <div className={styles.success}>{notice}</div>}

        <div className={styles.actions}>
          <Link to="/admin/tours" className={styles.secondaryBtn}>
            Cancel
          </Link>
          <button
            type="submit"
            className={styles.primaryBtn}
            disabled={saving || !hasChanges}
          >
            {saving ? "Saving…" : mode === "create" ? "Create" : "Save"}
          </button>
        </div>
      </form>

      {mode === "edit" && canEditImages && (
        <ImageManager
          tourId={tourId}
          images={images}
          setImages={setImages}
        />
      )}
    </div>
  );
}

function ImageManager({ tourId, images, setImages }) {
  const [file, setFile] = useState(null);
  const [imageAlt, setImageAlt] = useState("");
  const [useAsThumb, setUseAsThumb] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file || !imageAlt) return;
    setBusy(true);
    setError(null);
    try {
      const created = await uploadTourImage(tourId, file, {
        imageAlt,
        sortOrder: images.length,
        useAsThumbnail: useAsThumb,
      });
      setImages([...images, created]);
      setFile(null);
      setImageAlt("");
      setUseAsThumb(false);
      e.target.reset();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(image) {
    if (!confirm(`Delete image "${image.image_alt}"?`)) return;
    try {
      await deleteTourImage(tourId, image.id);
      setImages(images.filter((i) => i.id !== image.id));
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggleThumbnail(image) {
    try {
      const updated = await updateTourImage(tourId, image.id, {
        use_as_thumbnail: !image.use_as_thumbnail,
      });
      setImages(images.map((i) => (i.id === image.id ? updated : i)));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className={styles.imageSection}>
      <h2>Images</h2>
      <p style={{ fontSize: "0.85rem", color: "var(--color-muted)" }}>
        PNG or JPEG, up to 10 MB.
      </p>

      <form onSubmit={handleUpload} style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "flex-end", marginTop: "0.5rem" }}>
        <input
          type="file"
          accept="image/png,image/jpeg"
          onChange={(e) => setFile(e.target.files[0] ?? null)}
          required
        />
        <input
          className={styles.input}
          style={{ flex: "1 1 200px" }}
          placeholder="Alt text (required)"
          maxLength={255}
          value={imageAlt}
          onChange={(e) => setImageAlt(e.target.value)}
          required
        />
        <label style={{ display: "flex", gap: "0.3rem", alignItems: "center", fontSize: "0.85rem" }}>
          <input
            type="checkbox"
            checked={useAsThumb}
            onChange={(e) => setUseAsThumb(e.target.checked)}
          />
          Thumbnail
        </label>
        <button type="submit" className={styles.primaryBtn} disabled={busy || !file || !imageAlt}>
          {busy ? "Uploading…" : "Upload"}
        </button>
      </form>

      {error && <div className={styles.error} style={{ marginTop: "0.75rem" }}>{error}</div>}

      <div className={styles.imageList}>
        {images.map((image) => (
          <div key={image.id} className={styles.imageCard}>
            <img src={image.image_url} alt={image.image_alt} />
            <div className={styles.imageCardBody}>
              <div title={image.image_alt} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {image.image_alt}
              </div>
              <div className={styles.imageCardActions}>
                <label style={{ display: "flex", gap: "0.3rem", alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={image.use_as_thumbnail}
                    onChange={() => toggleThumbnail(image)}
                  />
                  Thumb
                </label>
                <button
                  type="button"
                  className={styles.dangerBtn}
                  onClick={() => handleDelete(image)}
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
