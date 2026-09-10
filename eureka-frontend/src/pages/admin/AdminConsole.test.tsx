import { describe, it, expect, afterEach } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import AdminConsole from '../../pages/admin/AdminConsole';
import { useAuthStore } from '../../store/authStore';

afterEach(() => useAuthStore.setState({ status: 'unauthenticated', user: null }));

describe('AdminConsole — light professional EUREKA Users surface', () => {
  it('renders breadcrumb, title, subtitle, tabs and export (no network on SSR)', () => {
    const html = renderToString(createElement(MemoryRouter, null, createElement(AdminConsole)));
    expect(html).toContain('User Management');
    expect(html).toContain('Manage accounts, roles and activity across the EUREKA platform.');
    expect(html).toContain('Users');
    expect(html).toContain('Reports');
    expect(html).toContain('Audit');
    expect(html.toLowerCase()).toContain('search by name');
    expect(html).toContain('Export to Excel');
  });
});
