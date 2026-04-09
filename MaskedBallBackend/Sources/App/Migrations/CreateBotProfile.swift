import Fluent

struct CreateBotProfile: AsyncMigration {
    func prepare(on database: Database) async throws {
        try await database.schema("bot_profiles")
            .id()
            .field("name", .string, .required)
            .field("personality", .string, .required)
            .field("language_style", .string, .required)
            .field("bio", .string, .required)
            .field("keywords", .array(of: .string), .required)
            .field("greeting", .string, .required)
            .field("view_count", .int, .required)
            .field("chat_count", .int, .required)
            .field("created_at", .datetime, .required)
            .field("user_id", .uuid, .required, .references("users", "id"))
            .create()
    }
    
    func revert(on database: Database) async throws {
        try await database.schema("bot_profiles").delete()
    }
}