import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <section className="page page-home">
      <h1>Welcome to Lolo Tours</h1>
      <p>Unforgettable guided experiences. Book a slot and come along.</p>
      <Link to="/schedule" className="cta">See available tours</Link>
    </section>
  );
}
