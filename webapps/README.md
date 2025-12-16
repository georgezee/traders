# Webapp / Svelte placeholder

This folder is a placeholder for interactive functionality through a
framework such as Svelte

```
webapps/
├── traders-app/
│   ├── src/
│   │   ├── main.ts              # Application entry point
│   │   ├── App.svelte           # Root component
│   │   ├── app.css              # Global styles
│   │   ├── lib/
│   │   │   ├── api.ts           # API client
│   │   │   ├── constants.ts     # Application constants
│   │   │   ├── telemetry.ts     # Event tracking
│   │   │   ├── types.ts         # TypeScript types
│   │   │   └── utils.ts         # Utility functions
│   │   ├── stores/
│   │   │   └── globalConfig.svelte.ts  # Global configuration
│   │   ├── contexts/
│   │   │   └── uiContext.svelte.ts      # UI state
│   │   ├── components/
│   │   │   ├── nodes/           # Custom SvelteFlow nodes
│   │   │   ├── ui/              # UI components
│   │   │   └── shared/          # Shared components
│   │   └── mocks/               # Mock API data
│   └── index.html               # HTML entry point
├── package.json                 # Dependencies
├── tsconfig.json                # TypeScript config
├── .env                         # Environment variables
└── .env.example                 # Example environment file
```

## Setup

1. Install dependencies:
```bash
cd webapps
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env
```

3. Run the development server:
```bash
npm run dev:traders-app
```

4. Build for production:
```bash
npm run build:traders-app
```

## Environment Variables

- `VITE_API_BASE_URL`: API base URL (default: `/api`)


## Development

### Watching for code changes.
```bash
npm run watch:build
```

## Troubleshooting

### Debug Mode

Set `VITE_USE_MOCK_DATA=true` to run without backend dependencies.

## License

This project is part of the Traders platform.