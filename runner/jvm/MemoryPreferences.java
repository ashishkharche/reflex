// In-memory java.util.prefs for Reflex CLI runs. On macOS the JVM keeps
// Preferences in the account's plist and ignores user.home, so a CLI could
// read or change the real user's settings. The runner loads this factory so
// every run starts empty and nothing is saved.
package reflex.prefs;

import java.util.HashMap;
import java.util.Map;
import java.util.prefs.AbstractPreferences;
import java.util.prefs.Preferences;
import java.util.prefs.PreferencesFactory;

public final class MemoryPreferences extends AbstractPreferences {
    private final Map<String, String> values = new HashMap<>();
    private final Map<String, MemoryPreferences> children = new HashMap<>();

    MemoryPreferences(MemoryPreferences parent, String name) {
        super(parent, name);
    }

    @Override protected void putSpi(String key, String value) { values.put(key, value); }
    @Override protected String getSpi(String key) { return values.get(key); }
    @Override protected void removeSpi(String key) { values.remove(key); }
    @Override protected void removeNodeSpi() { values.clear(); children.clear(); }
    @Override protected String[] keysSpi() { return values.keySet().toArray(new String[0]); }
    @Override protected String[] childrenNamesSpi() { return children.keySet().toArray(new String[0]); }
    @Override protected AbstractPreferences childSpi(String name) {
        return children.computeIfAbsent(name, n -> new MemoryPreferences(this, n));
    }
    @Override protected void syncSpi() { }
    @Override protected void flushSpi() { }

    public static final class Factory implements PreferencesFactory {
        private static final Preferences USER = new MemoryPreferences(null, "");
        private static final Preferences SYSTEM = new MemoryPreferences(null, "");
        @Override public Preferences userRoot() { return USER; }
        @Override public Preferences systemRoot() { return SYSTEM; }
    }
}
