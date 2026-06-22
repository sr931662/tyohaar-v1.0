import {
  Gift, Utensils, Coffee, UserCheck, Camera, Video,
  Music2, Headphones, Mail, Cake, Lightbulb, Users, Sparkles,
} from 'lucide-react';

const MAP = {
  Decorations: Gift,
  Catering:    Utensils,
  Pantry:      Coffee,
  Waiters:     UserCheck,
  Photography: Camera,
  Videography: Video,
  Music:       Music2,
  DJ:          Headphones,
  Invitations: Mail,
  Cakes:       Cake,
  Lighting:    Lightbulb,
  Seating:     Users,
  Cleanup:     Sparkles,
};

export default function ServiceIcon({ name, size = 22, strokeWidth = 1.8 }) {
  const Icon = MAP[name];
  if (!Icon) return null;
  return <Icon size={size} strokeWidth={strokeWidth} aria-hidden="true" />;
}
