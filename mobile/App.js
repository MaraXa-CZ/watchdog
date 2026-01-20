/**
 * Watchdog Mobile App v4.0
 * React Native companion app for Watchdog Network Monitoring System
 * 
 * © 2026 MaraXa
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  RefreshControl,
  StatusBar,
  ActivityIndicator,
  Switch,
  SafeAreaView,
  Platform,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// ==================== Configuration ====================
const APP_VERSION = '4.0.0';
const STORAGE_KEYS = {
  SERVER_URL: 'watchdog_server_url',
  API_TOKEN: 'watchdog_api_token',
  LANGUAGE: 'watchdog_language',
  THEME: 'watchdog_theme',
};

// ==================== Translations ====================
const translations = {
  cs: {
    app_name: 'Watchdog',
    login: 'Přihlášení',
    logout: 'Odhlásit',
    username: 'Uživatelské jméno',
    password: 'Heslo',
    server_url: 'URL serveru',
    connect: 'Připojit',
    dashboard: 'Dashboard',
    groups: 'Skupiny',
    logs: 'Logy',
    settings: 'Nastavení',
    refresh: 'Obnovit',
    no_groups: 'Žádné aktivní skupiny',
    servers: 'Servery',
    fail_count: 'Pokusy',
    off_time: 'Výpadek',
    on: 'ZAP',
    off: 'VYP',
    restart: 'RESTART',
    confirm_restart: 'Opravdu restartovat skupinu',
    command_sent: 'Příkaz odeslán',
    error: 'Chyba',
    connection_error: 'Chyba připojení',
    invalid_credentials: 'Neplatné přihlašovací údaje',
    language: 'Jazyk',
    theme: 'Motiv',
    dark: 'Tmavý',
    light: 'Světlý',
    version: 'Verze',
    uptime: 'Uptime',
    resets: 'Resetů',
    stats: 'Statistiky',
    online: 'Online',
    offline: 'Offline',
    loading: 'Načítání...',
    save: 'Uložit',
    cancel: 'Zrušit',
  },
  en: {
    app_name: 'Watchdog',
    login: 'Login',
    logout: 'Logout',
    username: 'Username',
    password: 'Password',
    server_url: 'Server URL',
    connect: 'Connect',
    dashboard: 'Dashboard',
    groups: 'Groups',
    logs: 'Logs',
    settings: 'Settings',
    refresh: 'Refresh',
    no_groups: 'No active groups',
    servers: 'Servers',
    fail_count: 'Fail count',
    off_time: 'Off time',
    on: 'ON',
    off: 'OFF',
    restart: 'RESTART',
    confirm_restart: 'Really restart group',
    command_sent: 'Command sent',
    error: 'Error',
    connection_error: 'Connection error',
    invalid_credentials: 'Invalid credentials',
    language: 'Language',
    theme: 'Theme',
    dark: 'Dark',
    light: 'Light',
    version: 'Version',
    uptime: 'Uptime',
    resets: 'Resets',
    stats: 'Statistics',
    online: 'Online',
    offline: 'Offline',
    loading: 'Loading...',
    save: 'Save',
    cancel: 'Cancel',
  },
};

// ==================== Theme Colors ====================
const themes = {
  dark: {
    background: '#1e1e1e',
    surface: '#252526',
    card: '#2d2d2d',
    border: '#3c3c3c',
    text: '#cccccc',
    textSecondary: '#858585',
    accent: '#0e7c7b',
    success: '#28a745',
    danger: '#dc3545',
    warning: '#ffc107',
  },
  light: {
    background: '#f5f5f5',
    surface: '#ffffff',
    card: '#ffffff',
    border: '#d0d0d0',
    text: '#333333',
    textSecondary: '#666666',
    accent: '#0e7c7b',
    success: '#28a745',
    danger: '#dc3545',
    warning: '#ffc107',
  },
};

// ==================== API Client ====================
class WatchdogAPI {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.token = token;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  async login(username, password) {
    return this.request('/api/auth', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async getStatus() {
    return this.request('/api/status');
  }

  async getGroups() {
    return this.request('/api/groups');
  }

  async control(groupName, action) {
    return this.request('/api/control', {
      method: 'POST',
      body: JSON.stringify({ group: groupName, action }),
    });
  }

  async getStats(groupName, days = 1) {
    return this.request(`/api/stats/${encodeURIComponent(groupName)}?days=${days}`);
  }
}

// ==================== Main App Component ====================
export default function App() {
  // State
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [serverUrl, setServerUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [apiToken, setApiToken] = useState('');
  const [language, setLanguage] = useState('cs');
  const [themeName, setThemeName] = useState('dark');
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [groups, setGroups] = useState([]);
  const [outlets, setOutlets] = useState({});
  const [stats, setStats] = useState({});
  const [refreshing, setRefreshing] = useState(false);
  const [user, setUser] = useState(null);

  const theme = themes[themeName];
  const t = translations[language];
  const api = apiToken ? new WatchdogAPI(serverUrl, apiToken) : null;

  // Load saved settings
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const savedUrl = await AsyncStorage.getItem(STORAGE_KEYS.SERVER_URL);
      const savedToken = await AsyncStorage.getItem(STORAGE_KEYS.API_TOKEN);
      const savedLang = await AsyncStorage.getItem(STORAGE_KEYS.LANGUAGE);
      const savedTheme = await AsyncStorage.getItem(STORAGE_KEYS.THEME);

      if (savedUrl) setServerUrl(savedUrl);
      if (savedLang) setLanguage(savedLang);
      if (savedTheme) setThemeName(savedTheme);
      
      if (savedUrl && savedToken) {
        setApiToken(savedToken);
        setIsAuthenticated(true);
      }
    } catch (e) {
      console.error('Error loading settings:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const saveSettings = async (key, value) => {
    try {
      await AsyncStorage.setItem(key, value);
    } catch (e) {
      console.error('Error saving settings:', e);
    }
  };

  // Login
  const handleLogin = async () => {
    if (!serverUrl || !username || !password) {
      Alert.alert(t.error, 'Please fill all fields');
      return;
    }

    setIsLoading(true);
    try {
      const tempApi = new WatchdogAPI(serverUrl, null);
      const result = await tempApi.login(username, password);

      if (result.success && result.token) {
        setApiToken(result.token);
        setUser(result.user);
        setIsAuthenticated(true);
        await saveSettings(STORAGE_KEYS.SERVER_URL, serverUrl);
        await saveSettings(STORAGE_KEYS.API_TOKEN, result.token);
        loadData();
      } else {
        Alert.alert(t.error, t.invalid_credentials);
      }
    } catch (error) {
      Alert.alert(t.error, t.connection_error);
    } finally {
      setIsLoading(false);
    }
  };

  // Logout
  const handleLogout = async () => {
    await AsyncStorage.removeItem(STORAGE_KEYS.API_TOKEN);
    setApiToken('');
    setIsAuthenticated(false);
    setUser(null);
    setGroups([]);
  };

  // Load data
  const loadData = useCallback(async () => {
    if (!api) return;

    setRefreshing(true);
    try {
      const groupsData = await api.getGroups();
      setGroups(groupsData.groups || []);
      setOutlets(groupsData.outlets || {});

      // Load stats for each enabled group
      const newStats = {};
      for (const group of groupsData.groups.filter(g => g.enabled)) {
        try {
          const groupStats = await api.getStats(group.name, 1);
          newStats[group.name] = groupStats.summary;
        } catch (e) {
          console.log('Stats error for', group.name);
        }
      }
      setStats(newStats);
    } catch (error) {
      Alert.alert(t.error, t.connection_error);
    } finally {
      setRefreshing(false);
    }
  }, [api, t]);

  useEffect(() => {
    if (isAuthenticated && api) {
      loadData();
    }
  }, [isAuthenticated]);

  // Control relay
  const handleControl = async (groupName, action) => {
    if (action === 'restart') {
      Alert.alert(
        t.restart,
        `${t.confirm_restart} "${groupName}"?`,
        [
          { text: t.cancel, style: 'cancel' },
          {
            text: t.restart,
            style: 'destructive',
            onPress: () => executeControl(groupName, action),
          },
        ]
      );
    } else {
      executeControl(groupName, action);
    }
  };

  const executeControl = async (groupName, action) => {
    try {
      await api.control(groupName, action);
      Alert.alert(t.command_sent);
    } catch (error) {
      Alert.alert(t.error, t.connection_error);
    }
  };

  // Render Login Screen
  const renderLogin = () => (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <View style={[styles.loginCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <Text style={[styles.title, { color: theme.accent }]}>⚡ {t.app_name}</Text>
        <Text style={[styles.subtitle, { color: theme.textSecondary }]}>Network Monitoring</Text>

        <TextInput
          style={[styles.input, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
          placeholder={t.server_url}
          placeholderTextColor={theme.textSecondary}
          value={serverUrl}
          onChangeText={setServerUrl}
          autoCapitalize="none"
          keyboardType="url"
        />

        <TextInput
          style={[styles.input, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
          placeholder={t.username}
          placeholderTextColor={theme.textSecondary}
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
        />

        <TextInput
          style={[styles.input, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
          placeholder={t.password}
          placeholderTextColor={theme.textSecondary}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity
          style={[styles.button, { backgroundColor: theme.accent }]}
          onPress={handleLogin}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>{t.connect}</Text>
          )}
        </TouchableOpacity>

        <View style={styles.langSwitch}>
          <TouchableOpacity onPress={() => { setLanguage('cs'); saveSettings(STORAGE_KEYS.LANGUAGE, 'cs'); }}>
            <Text style={[styles.langBtn, language === 'cs' && styles.langActive]}>🇨🇿</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => { setLanguage('en'); saveSettings(STORAGE_KEYS.LANGUAGE, 'en'); }}>
            <Text style={[styles.langBtn, language === 'en' && styles.langActive]}>🇬🇧</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );

  // Render Dashboard
  const renderDashboard = () => {
    const enabledGroups = groups.filter(g => g.enabled);

    return (
      <ScrollView
        style={[styles.content, { backgroundColor: theme.background }]}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={loadData} tintColor={theme.accent} />
        }
      >
        {enabledGroups.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={[styles.emptyText, { color: theme.textSecondary }]}>{t.no_groups}</Text>
          </View>
        ) : (
          enabledGroups.map((group, index) => (
            <View key={index} style={[styles.card, { backgroundColor: theme.card, borderColor: theme.border }]}>
              <Text style={[styles.cardTitle, { color: theme.accent }]}>{group.name}</Text>

              <View style={styles.cardInfo}>
                <Text style={{ color: theme.textSecondary }}>
                  {t.servers}: {group.servers?.join(', ') || '-'}
                </Text>
                <Text style={{ color: theme.textSecondary }}>
                  {t.fail_count}: {group.fail_count} | {t.off_time}: {group.off_time}s
                </Text>
              </View>

              {stats[group.name] && (
                <View style={[styles.statsRow, { backgroundColor: theme.background }]}>
                  <Text style={{ color: theme.text }}>
                    📊 {t.uptime}: <Text style={{ fontWeight: 'bold' }}>{stats[group.name].uptime_percent}%</Text>
                  </Text>
                  <Text style={{ color: theme.text }}>
                    {t.resets}: {stats[group.name].total_resets}
                  </Text>
                </View>
              )}

              {user?.permissions?.includes('control_relays') && (
                <View style={styles.controlButtons}>
                  <TouchableOpacity
                    style={[styles.controlBtn, { backgroundColor: theme.success }]}
                    onPress={() => handleControl(group.name, 'on')}
                  >
                    <Text style={styles.controlBtnText}>{t.on}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.controlBtn, { backgroundColor: theme.danger }]}
                    onPress={() => handleControl(group.name, 'off')}
                  >
                    <Text style={styles.controlBtnText}>{t.off}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.controlBtn, { backgroundColor: theme.warning }]}
                    onPress={() => handleControl(group.name, 'restart')}
                  >
                    <Text style={[styles.controlBtnText, { color: '#1e1e1e' }]}>{t.restart}</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          ))
        )}
      </ScrollView>
    );
  };

  // Render Settings
  const renderSettings = () => (
    <ScrollView style={[styles.content, { backgroundColor: theme.background }]}>
      <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.border }]}>
        <Text style={[styles.cardTitle, { color: theme.accent }]}>{t.settings}</Text>

        {user && (
          <View style={styles.settingRow}>
            <Text style={{ color: theme.text }}>👤 {user.username}</Text>
            <Text style={{ color: theme.textSecondary }}>{user.role}</Text>
          </View>
        )}

        <View style={styles.settingRow}>
          <Text style={{ color: theme.text }}>{t.language}</Text>
          <View style={styles.langSwitch}>
            <TouchableOpacity onPress={() => { setLanguage('cs'); saveSettings(STORAGE_KEYS.LANGUAGE, 'cs'); }}>
              <Text style={[styles.langBtn, language === 'cs' && styles.langActive]}>🇨🇿</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => { setLanguage('en'); saveSettings(STORAGE_KEYS.LANGUAGE, 'en'); }}>
              <Text style={[styles.langBtn, language === 'en' && styles.langActive]}>🇬🇧</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.settingRow}>
          <Text style={{ color: theme.text }}>{t.theme}</Text>
          <View style={styles.langSwitch}>
            <TouchableOpacity onPress={() => { setThemeName('dark'); saveSettings(STORAGE_KEYS.THEME, 'dark'); }}>
              <Text style={[styles.langBtn, themeName === 'dark' && styles.langActive]}>🌙</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => { setThemeName('light'); saveSettings(STORAGE_KEYS.THEME, 'light'); }}>
              <Text style={[styles.langBtn, themeName === 'light' && styles.langActive]}>☀️</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.settingRow}>
          <Text style={{ color: theme.text }}>{t.server_url}</Text>
          <Text style={{ color: theme.textSecondary, fontSize: 12 }}>{serverUrl}</Text>
        </View>

        <TouchableOpacity
          style={[styles.button, { backgroundColor: theme.danger, marginTop: 20 }]}
          onPress={handleLogout}
        >
          <Text style={styles.buttonText}>{t.logout}</Text>
        </TouchableOpacity>

        <Text style={[styles.version, { color: theme.textSecondary }]}>
          {t.version} {APP_VERSION}
        </Text>
      </View>
    </ScrollView>
  );

  // Main render
  if (isLoading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.accent} />
      </View>
    );
  }

  if (!isAuthenticated) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }}>
        <StatusBar barStyle={themeName === 'dark' ? 'light-content' : 'dark-content'} />
        {renderLogin()}
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }}>
      <StatusBar barStyle={themeName === 'dark' ? 'light-content' : 'dark-content'} />

      {/* Header */}
      <View style={[styles.header, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <Text style={[styles.headerTitle, { color: theme.accent }]}>⚡ {t.app_name}</Text>
      </View>

      {/* Content */}
      {currentTab === 'dashboard' && renderDashboard()}
      {currentTab === 'settings' && renderSettings()}

      {/* Tab Bar */}
      <View style={[styles.tabBar, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.tab, currentTab === 'dashboard' && { borderTopColor: theme.accent, borderTopWidth: 2 }]}
          onPress={() => setCurrentTab('dashboard')}
        >
          <Text style={{ color: currentTab === 'dashboard' ? theme.accent : theme.textSecondary, fontSize: 20 }}>🏠</Text>
          <Text style={{ color: currentTab === 'dashboard' ? theme.accent : theme.textSecondary, fontSize: 11 }}>
            {t.dashboard}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tab, currentTab === 'settings' && { borderTopColor: theme.accent, borderTopWidth: 2 }]}
          onPress={() => setCurrentTab('settings')}
        >
          <Text style={{ color: currentTab === 'settings' ? theme.accent : theme.textSecondary, fontSize: 20 }}>⚙️</Text>
          <Text style={{ color: currentTab === 'settings' ? theme.accent : theme.textSecondary, fontSize: 11 }}>
            {t.settings}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

// ==================== Styles ====================
const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loginCard: {
    width: '100%',
    maxWidth: 400,
    padding: 30,
    borderRadius: 8,
    borderWidth: 1,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 30,
  },
  input: {
    height: 48,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 15,
    marginBottom: 15,
    fontSize: 16,
  },
  button: {
    height: 48,
    borderRadius: 4,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  header: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderBottomWidth: 1,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  content: {
    flex: 1,
    padding: 15,
  },
  card: {
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 15,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 10,
  },
  cardInfo: {
    marginBottom: 10,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 10,
    borderRadius: 4,
    marginBottom: 10,
  },
  controlButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 8,
  },
  controlBtn: {
    flex: 1,
    height: 40,
    borderRadius: 4,
    justifyContent: 'center',
    alignItems: 'center',
  },
  controlBtnText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  tabBar: {
    flexDirection: 'row',
    height: 60,
    borderTopWidth: 1,
  },
  tab: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyState: {
    padding: 40,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
  },
  langSwitch: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 20,
    gap: 15,
  },
  langBtn: {
    fontSize: 24,
    opacity: 0.5,
  },
  langActive: {
    opacity: 1,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#3c3c3c',
  },
  version: {
    textAlign: 'center',
    marginTop: 30,
    fontSize: 12,
  },
});
