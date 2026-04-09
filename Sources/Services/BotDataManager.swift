import Foundation

class BotDataManager {
    static let shared = BotDataManager()
    
    private let defaults = UserDefaults.standard
    private let botConfigKey = "botConfiguration"
    private let userKey = "currentUser"
    
    private init() {}
    
    func saveBotConfiguration(_ config: BotConfiguration) {
        if let encoded = try? JSONEncoder().encode(config) {
            defaults.set(encoded, forKey: botConfigKey)
        }
    }
    
    func loadBotConfiguration() -> BotConfiguration? {
        guard let data = defaults.data(forKey: botConfigKey),
              let config = try? JSONDecoder().decode(BotConfiguration.self, from: data) else {
            return nil
        }
        return config
    }
    
    func saveUser(_ user: User) {
        if let encoded = try? JSONEncoder().encode(user) {
            defaults.set(encoded, forKey: userKey)
        }
    }
    
    func loadUser() -> User? {
        guard let data = defaults.data(forKey: userKey),
              let user = try? JSONDecoder().decode(User.self, from: data) else {
            return nil
        }
        return user
    }
    
    func clearAllData() {
        defaults.removeObject(forKey: botConfigKey)
        defaults.removeObject(forKey: userKey)
    }
}