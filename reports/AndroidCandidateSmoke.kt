// Compile with the unchanged Android MmaModels.kt, EventJsonParser.kt and EventValidator.kt.
// This is a JVM parser/validator smoke test, not an Android emulator or device test.
import com.example.data.model.EventStatus
import com.example.data.model.FightResult
import com.example.data.parser.EventJsonParser
import com.example.data.validator.EventValidator
import java.io.File
import org.json.JSONObject

fun main(args: Array<String>) {
    val raw = File(args.single()).readText(Charsets.UTF_8)
    val event = EventJsonParser.parse(raw)
    val checks = mutableListOf<String>()
    fun passed(name: String, test: () -> Unit) { test(); checks += name }
    passed("Exact candidate parses and validates as DRAFT") {
        check(event.status == EventStatus.DRAFT && !event.isSampleData)
        val report = EventValidator.validate(event)
        check(report.isValid && report.errors.isEmpty() && report.warnings.isEmpty()) { report.toString() }
    }
    val fighters = event.fights.flatMap { listOf(it.fighterA, it.fighterB) }
    passed("12 bouts, 24 unique fighters, 48 histories and all event headliners") {
        check(event.fights.size == 12 && fighters.size == 24)
        check(fighters.map { it.id }.toSet().size == 24)
        check(fighters.map { it.fullName }.toSet().size == 24)
        check(fighters.sumOf { it.lastTwoFights.size } == 48)
        check(fighters.flatMap { it.lastTwoFights }.all { !it.eventHeadliners.isNullOrBlank() })
    }
    passed("UFC/ESPN chronological card contract: seven prelims then five main bouts") {
        check(event.fights.take(7).all { it.cardType == "PRELIMS" })
        check(event.fights.drop(7).map { it.cardType } == listOf("MAIN_CARD", "MAIN_CARD", "MAIN_CARD", "CO_MAIN_EVENT", "MAIN_EVENT"))
        check(event.fights.last().fighterA.fullName == "Renato Moicano")
        check(event.fights.last().fighterB.fullName == "Tom Nolan")
        check(event.fights.last().scheduledRounds == 5)
    }
    passed("Core data survives the existing parser/toJson round trip") {
        check(EventJsonParser.parse(EventJsonParser.toJson(event)) == event)
        // The existing Android model intentionally does not round-trip research metadata.
    }
    passed("Documented NC and professional-only history corrections are preserved") {
        val ode = fighters.single { it.id == "ode-osbourne" }
        check(ode.record.noContests == 2)
        check(ode.lastTwoFights.first().result == FightResult.NO_CONTEST)
        val rodrigo = fighters.single { it.id == "rodrigo-sezinando" }
        check(rodrigo.record.wins == 8 && rodrigo.lastTwoFights[1].opponentName == "Jonathan Ramsay")
        check(fighters.single { it.id == "julian-erosa" }.record.losses == 13)
    }
    passed("DRAFT fails publication status gate; in-memory published structural preflight passes") {
        check(!EventValidator.validate(event, publication = true).isValid)
        check(EventValidator.validate(event.copy(status = EventStatus.PUBLISHED), publication = true).isValid)
        // No file, approval, manifest or network is written by this preflight.
    }
    passed("Wrong JSON numeric types are rejected by the actual parser") {
        for (value in listOf<Any>("12", true)) {
            val root = JSONObject(raw)
            root.getJSONArray("fights").getJSONObject(0).getJSONObject("fighterA").getJSONObject("record").put("wins", value)
            check(runCatching { EventJsonParser.parse(root.toString()) }.isFailure)
        }
    }
    passed("Missing historical headliners and duplicate fighter identities are rejected") {
        val missing = JSONObject(raw)
        missing.getJSONArray("fights").getJSONObject(0).getJSONObject("fighterA").getJSONArray("lastTwoFights").getJSONObject(0).remove("eventHeadliners")
        val parsedMissing = EventJsonParser.parse(missing.toString())
        check(EventValidator.validate(parsedMissing).warnings.isNotEmpty())
        check(!EventValidator.validate(parsedMissing.copy(status = EventStatus.PUBLISHED), publication = true).isValid)
        val duplicate = JSONObject(raw)
        val bout = duplicate.getJSONArray("fights").getJSONObject(0)
        bout.getJSONObject("fighterB").put("id", bout.getJSONObject("fighterA").getString("id"))
        check(!EventValidator.validate(EventJsonParser.parse(duplicate.toString())).isValid)
    }
    passed("Future history dates are rejected") {
        val root = JSONObject(raw)
        root.getJSONArray("fights").getJSONObject(0).getJSONObject("fighterA").getJSONArray("lastTwoFights").getJSONObject(0).put("date", "2027-01-01")
        check(!EventValidator.validate(EventJsonParser.parse(root.toString())).isValid)
    }
    checks.forEach { println("PASS: $it") }
    println("PASS: ${checks.size} Android production parser/validator checks")
}
