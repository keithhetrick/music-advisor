#include "AnimatedSvgBadge.h"

namespace {
const char *badgeSvg = R"SVG(
<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4DB6FF"/>
      <stop offset="100%" stop-color="#7C4DFF"/>
    </linearGradient>
  </defs>
  <circle cx="32" cy="32" r="28" stroke="url(#g1)" stroke-width="4" fill="none"/>
  <path d="M32 12 L40 36 L32 52 L24 36 Z" fill="#4DB6FF" opacity="0.85"/>
  <circle cx="32" cy="32" r="6" fill="#FFFFFF"/>
</svg>
)SVG";

std::unique_ptr<juce::Drawable> makeBadgeDrawable() {
  auto xml = juce::parseXML(badgeSvg);
  if (!xml)
    return {};
  return juce::Drawable::createFromSVG(*xml);
}
} // namespace

AnimatedSvgBadge::AnimatedSvgBadge() {
  drawable = makeBadgeDrawable();
  startTimerHz(30);
}

void AnimatedSvgBadge::paint(juce::Graphics &g) {
  g.fillAll(juce::Colour::fromRGBA(0, 0, 0, 0));
  if (!drawable)
    return;
  auto b = getLocalBounds().toFloat().reduced(4.0f);
  auto alpha = 0.75f + 0.25f * std::sin(phase);
  drawable->setTransform(juce::AffineTransform::rotation(0.05f * std::sin(phase), b.getCentreX(), b.getCentreY())
                             .scaled(1.0f + 0.02f * std::sin(phase * 0.5f), 1.0f + 0.02f * std::sin(phase * 0.5f),
                                     b.getCentreX(), b.getCentreY()));
  drawable->draw(g, alpha);
}

void AnimatedSvgBadge::resized() {
  if (drawable)
    drawable->setBounds(getLocalBounds().toFloat().toNearestInt());
}

void AnimatedSvgBadge::timerCallback() {
  phase += 0.1f;
  repaint();
}
