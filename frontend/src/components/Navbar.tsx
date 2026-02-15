import { Shield, Menu, X } from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { Button } from "@/components/ui/button";
import { useState } from "react";

export const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2 group">
            <div className="relative">
              <Shield className="w-8 h-8 text-primary" />
              <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full" />
            </div>
            <span className="text-2xl font-display font-bold">
              VESTI<span className="text-primary">GO</span>
            </span>
          </NavLink>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <NavLink
              to="/"
              className="text-muted-foreground hover:text-foreground transition-colors"
              activeClassName="text-primary font-medium"
            >
              Home
            </NavLink>

            <NavLink
              to="/how-it-works"
              className="text-muted-foreground hover:text-foreground transition-colors"
              activeClassName="text-primary font-medium"
            >
              How It Works
            </NavLink>

            <NavLink
              to="/upload"
              className="text-muted-foreground hover:text-foreground transition-colors"
              activeClassName="text-primary font-medium"
            >
              Upload Firmware
            </NavLink>

            <NavLink
              to="/jobs"
              className="text-muted-foreground hover:text-foreground transition-colors"
              activeClassName="text-primary font-medium"
            >
              Analysis Jobs
            </NavLink>
          </div>

          {/* CTA Button */}
          <div className="hidden md:block">
            <NavLink to="/upload">
              <Button className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold">
                Start Analysis
              </Button>
            </NavLink>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="md:hidden text-foreground"
          >
            {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="md:hidden pt-4 pb-2 space-y-3">
            <NavLink
              to="/"
              className="block py-2 text-muted-foreground hover:text-foreground transition-colors"
              activeClassName="text-primary font-medium"
              onClick={() => setIsOpen(false)}
            >
              Home
            </NavLink>

            <NavLink
              to="/how-it-works"
              className="block py-2 text-muted-foreground hover:text-foreground transition-colors"
              activeClassName="text-primary font-medium"
              onClick={() => setIsOpen(false)}
            >
              How It Works
            </NavLink>

            <NavLink
              to="/upload"
              className="block py-2 text-muted-foreground hover:text-foreground transition-colors"
              activeClassName="text-primary font-medium"
              onClick={() => setIsOpen(false)}
            >
              Upload Firmware
            </NavLink>

            <NavLink
              to="/jobs"
              className="block py-2 text-muted-foreground hover:text-foreground transition-colors"
              activeClassName="text-primary font-medium"
              onClick={() => setIsOpen(false)}
            >
              Analysis Jobs
            </NavLink>

            <NavLink to="/upload" onClick={() => setIsOpen(false)}>
              <Button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-semibold mt-4">
                Start Analysis
              </Button>
            </NavLink>
          </div>
        )}
      </div>
    </nav>
  );
};
