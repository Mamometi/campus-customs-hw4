import { Link } from "react-router-dom";
import { MASCOT_FULL, openChat } from "../brand";

const YEAR = new Date().getFullYear();

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <div>
          <span className="footer__brand">Campus Customs</span>
          <p>
            Yale gear, printed and stitched in New Haven since 1975. A family business on Broadway, a short walk from
            Old Campus.
          </p>
        </div>
        <div>
          <strong>Shop</strong>
          <Link to="/products">All Products</Link>
          <Link to="/products?category=Hoodies">Hoodies</Link>
          <Link to="/products?category=Crewnecks">Crewnecks</Link>
          <Link to="/products?category=Quarter-Zips">Quarter-Zips</Link>
          <Link to="/products?category=T-Shirts">T-Shirts</Link>
        </div>
        <div>
          <strong>Company</strong>
          <Link to="/about">Our Story</Link>
          <Link to="/login">Login</Link>
          <Link to="/signup">Create Account</Link>
          <a
            href="#chat"
            onClick={(e) => {
              e.preventDefault();
              openChat();
            }}
          >
            Ask Handsome Dan
          </a>
        </div>
        <div>
          <strong>Visit</strong>
          <p>
            Broadway, New Haven, CT
            <br />
            Steps from Yale’s campus
          </p>
        </div>
        <img className="footer__dan" src={MASCOT_FULL} alt="" />
      </div>
      <p className="footer__legal">
        © {YEAR} Campus Customs · New Haven, Connecticut · Class project demo
      </p>
    </footer>
  );
}
