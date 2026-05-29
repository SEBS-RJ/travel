// ============================================================
// frontend/src/components/chat/QuickReplies.tsx
// Chips de respuesta rápida — sugerencias del asistente
// ============================================================

import React from "react";
import {
  ScrollView,
  TouchableOpacity,
  Text,
  StyleSheet,
  View,
} from "react-native";

interface Props {
  replies: string[];
  onSelect: (reply: string) => void;
}

export function QuickReplies({ replies, onSelect }: Props) {
  if (!replies || replies.length === 0) return null;

  return (
    <View style={styles.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scroll}
      >
        {replies.map((reply, index) => (
          <TouchableOpacity
            key={index}
            style={styles.chip}
            onPress={() => onSelect(reply)}
            activeOpacity={0.7}
          >
            <Text style={styles.chipText}>{reply}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 6,
    borderTopWidth: 1,
    borderTopColor: "#F3F4F6",
  },
  scroll: {
    paddingHorizontal: 12,
    gap: 8,
    flexDirection: "row",
  },
  chip: {
    backgroundColor: "#EFF6FF",
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderWidth: 1,
    borderColor: "#BFDBFE",
  },
  chipText: {
    fontSize: 13,
    color: "#1D4ED8",
    fontWeight: "500",
  },
});
