/**
 * Discord Join Page
 *
 * Displays Discord server embed/preview for Aurevia community
 */

import './DiscordJoin.css';

const DiscordJoin = () => {
  return (
    <div className="discord-page">
      <div className="discord-container">
        <div className="discord-header">
          <h1 className="discord-title">Join Aurevia Discord</h1>
          <p className="discord-subtitle">
            Connect with fellow traders, get real-time updates, and be part of the Aurevia community.
          </p>
        </div>

        <div className="discord-embed-container">
          <iframe
            src="https://discord.com/widget?id=1436767498971119687&theme=dark"
            width="350"
            height="500"
            allowtransparency="true"
            frameborder="0"
            sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts"
            title="Aurevia Discord Server"
            className="discord-widget"
          ></iframe>
        </div>

        <div className="discord-actions">
          <a
            href="https://discord.gg/kSj3hh7TKq"
            target="_blank"
            rel="noopener noreferrer"
            className="discord-join-button"
          >
            Join Discord Server
          </a>
          <p className="discord-note">
            Click the button above or use the widget to join our community.
          </p>
        </div>
      </div>
    </div>
  );
};

export default DiscordJoin;