package reflex.kit.auto

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import reflex.kit.JsonObject
import reflex.kit.Session
import reflex.kit.WireJson

interface NotesRepository {
    fun notes(): Flow<List<String>>
    suspend fun add(text: String)
}

class FakeNotesRepository : NotesRepository {
    private val items = MutableStateFlow(listOf("first"))
    override fun notes(): Flow<List<String>> = items
    override suspend fun add(text: String) { items.value = items.value + text }
}

interface Analytics { fun log(event: String) }

sealed interface Phase {
    object Loading : Phase
    data class Ready(val count: Int) : Phase
}

/** Like an Android ViewModel: a stateIn(WhileSubscribed) flow on Main, which stays frozen with no subscriber. */
class NotesViewModel(private val repository: NotesRepository, private val analytics: Analytics, val title: String = "Notes") {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    val notes: StateFlow<List<String>> = repository.notes().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val phase: StateFlow<Phase> = repository.notes().map<List<String>, Phase> { Phase.Ready(it.size) }
        .stateIn(scope, SharingStarted.WhileSubscribed(5000), Phase.Loading)
    fun add(text: String) { analytics.log("add"); scope.launch { repository.add(text) } }
    fun clearDraft() {}
}

class AutoHostTest {
    private val main = UnconfinedTestDispatcher()

    @Before fun setUp() = Dispatchers.setMain(main)
    @After fun tearDown() = Dispatchers.resetMain()

    private fun session(): Session {
        val config = AutoConfig(NotesViewModel::class.java.name, "Notes",
            fakes = listOf(FakeNotesRepository::class.java.name), params = mapOf("add/1" to listOf("text")))
        val builder = Builder(javaClass.classLoader, config.fakes, main)
        val vm = builder.construct(NotesViewModel::class.java, 0)
        assertTrue(builder.notes.toString(), builder.notes.any { it.contains("FakeNotesRepository") })
        assertTrue(builder.notes.toString(), builder.notes.any { it.contains("Analytics: stand-in") })
        val node = AutoNode(vm, config, CoroutineScope(SupervisorJob() + main)) { main.scheduler.runCurrent() }
        return Session("notes", { node })
    }

    @Test fun servesStateAndActionsWithNoAdapter() {
        val s = session()
        val hello = s.handle("""{"op":"hello","protocol":1}""") as JsonObject
        assertEquals(
            """{"actions":["Add","ClearDraft"],"inputs":{"Add":{"additionalProperties":false,"properties":{"text":{"type":"string"}},"required":["text"],"type":"object"}},"name":"Notes","state":{"notes":["first"],"phase":{"count":1,"type":"Ready"},"title":"Notes"}}""",
            hello["node"]!!.wire)
        val added = s.handle("""{"op":"do","action":"Add","input":{"text":"second"}}""") as JsonObject
        assertEquals("""{"notes":["first","second"],"phase":{"count":2,"type":"Ready"},"title":"Notes"}""", added["node"]!!["state"]!!.wire)
    }

    @Test fun rejectsBadInputLikeAnyHost() {
        val s = session()
        s.handle("""{"op":"hello","protocol":1}""")
        val bad = s.handle("""{"op":"do","action":"Add","input":{"text":1}}""") as JsonObject
        assertEquals("""{"code":"field.type","path":"$.input.text"}""", bad["error"]!!.wire)
    }

    @Test fun readsConfig() {
        val file = kotlin.io.path.createTempFile(suffix = ".json").toFile()
        file.writeText("""{"class":"a.b.HomeViewModel","name":"Home","fakes":["a.FakeX"],"params":{"open/1":["id"]},"omit":["now"]}""")
        val c = AutoConfig.read(file)
        assertEquals(listOf("id"), c.params["open/1"])
        assertEquals(setOf("now"), c.omit)
        assertEquals("Home", WireJson.parse("\"Home\"").let { c.name })
    }
}
