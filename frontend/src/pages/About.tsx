import { Link } from "react-router-dom";

const TIMELINE = [
  { year: "1975", text: "A small Yale memorabilia shop opens on Broadway, right across from campus." },
  { year: "Growing up", text: "Requests for custom gear lead us to bring screen printing, embroidery, and design in-house." },
  { year: "Today", text: "A second generation runs the business, still on Broadway and still family-owned." },
];

const VALUES = [
  {
    title: "Service first",
    text: "We treat every customer like a regular. Whether you're a first-year or a fifth-reunion alum, you'll get the same attention.",
  },
  {
    title: "Done under one roof",
    text: "Design, printing, and embroidery happen in our own shop. That means faster turnarounds and fewer surprises.",
  },
  {
    title: "Doing it right",
    text: "Fair dealing, honest pricing, and products we'd wear ourselves. That's how a family business lasts fifty years.",
  },
];

export default function About() {
  return (
    <div className="page about">
      <section className="about__intro">
        <span className="kicker">Our story</span>
        <h1>A New Haven family business, one shirt at a time.</h1>
        <p>
          Campus Customs started as a corner shop for Yale keepsakes. Students wanted their college crest on a
          sweatshirt, teams wanted matching gear, and parents wanted something to wear to The Game. We said yes
          to all of it, and learned to make it ourselves. Fifty years later, we're still a short walk from Old
          Campus, and still family-run.
        </p>
      </section>

      <section className="timeline">
        {TIMELINE.map((t) => (
          <div key={t.year} className="timeline__item">
            <span className="timeline__year">{t.year}</span>
            <p>{t.text}</p>
          </div>
        ))}
      </section>

      <section className="section highlights">
        {VALUES.map((v) => (
          <div key={v.title} className="highlight">
            <h3>{v.title}</h3>
            <p>{v.text}</p>
          </div>
        ))}
      </section>

      <section className="about__visit">
        <div>
          <h2>Come say hi</h2>
          <p>
            Our flagship store is on Broadway in New Haven, steps from Yale's campus. Stop in to try something on,
            or browse everything online.
          </p>
        </div>
        <Link to="/products" className="btn btn--primary">
          Browse the collection
        </Link>
      </section>
    </div>
  );
}
